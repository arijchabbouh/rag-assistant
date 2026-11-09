"""HTTP API on top of the existing pipeline (followup.ask_with_context).

Run:  uvicorn api:app --reload --port 8000
Docs: http://localhost:8000/docs
"""
import config  # noqa: F401  (reads .env into the environment, must come first)

import json
import logging
import os
import re
import threading
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, StringConstraints

logger = logging.getLogger("api")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

ALLOWED_ORIGINS = [o.strip() for o in os.environ.get("ALLOWED_ORIGINS", "http://localhost:5173").split(",")
                   if o.strip()]
FEEDBACK_FILE = Path(os.environ.get("FEEDBACK_FILE", "feedback.jsonl"))
RATE_LIMIT = 20          # requests...
RATE_WINDOW = 60.0       # ...per this many seconds, per client IP
STATUS_FILE = Path("documents_status.json")   # edited by hand; its "titre" fields name the sources

INTERNAL_ERROR = "Une erreur interne est survenue. Réessayez plus tard."
TOO_MANY = "Trop de requêtes. Attendez une minute puis réessayez."

# filled once by lifespan(): the modules of the pipeline (they load the model and the embeddings on import)
# and the documents' titles
pipeline = {}


def load_titles(path=STATUS_FILE):
    """{file name: title} from the "titre" fields of documents_status.json.
    A missing or empty title is left out: the file name is shown instead. A broken file gives no titles
    (and a warning in the logs) rather than stopping the API."""
    try:
        documents = json.loads(path.read_text(encoding="utf-8")).get("documents", {})
    except FileNotFoundError:
        return {}
    except (json.JSONDecodeError, UnicodeDecodeError, AttributeError) as e:
        logger.warning("%s cannot be read (%s): file names are shown instead of titles", path, e)
        return {}
    titles = {}
    for name, info in documents.items():
        title = info.get("titre") if isinstance(info, dict) else None
        if isinstance(title, str) and title.strip():
            titles[name] = title.strip()
    return titles


@asynccontextmanager
async def lifespan(app):
    if not os.environ.get("GEMINI_API_KEY"):
        # ask.py would call SystemExit on import; fail with a readable message instead
        raise RuntimeError("GEMINI_API_KEY is not set: copy .env.example to .env and put your key in it.")
    import ask            # its Gemini client has a timeout (ask.TIMEOUT_MS)
    import build_prompt
    import followup

    pipeline.update(ask=ask, build_prompt=build_prompt, followup=followup, titles=load_titles())
    logger.info("Pipeline loaded: %d chunks, embeddings %s, %d document titles", len(build_prompt.chunks),
                build_prompt.embeddings.shape, len(pipeline["titles"]))
    untitled = sorted({c["source"] for c in build_prompt.chunks} - set(pipeline["titles"]))
    if untitled:
        logger.warning("No \"titre\" in %s for: %s (file name shown instead)", STATUS_FILE, ", ".join(untitled))
    yield
    pipeline.clear()


app = FastAPI(title="Assistant ENICarthage", version="1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


@app.exception_handler(Exception)
async def unexpected_error(request: Request, exc: Exception):
    """Last safety net: the details go to the logs, never to the client."""
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": INTERNAL_ERROR})


# ------------------------------------------------------------------ rate limit

class RateLimiter:
    """At most `limit` requests per `window` seconds per IP, kept in memory (one process only)."""

    def __init__(self, limit, window):
        self.limit, self.window = limit, window
        self.hits = defaultdict(deque)
        self.lock = threading.Lock()

    def allow(self, key):
        now = time.monotonic()
        with self.lock:
            q = self.hits[key]
            while q and now - q[0] >= self.window:
                q.popleft()
            if len(q) >= self.limit:
                return False
            q.append(now)
            return True

    def reset(self):
        with self.lock:
            self.hits.clear()


limiter = RateLimiter(RATE_LIMIT, RATE_WINDOW)


def rate_limited(request: Request):
    ip = request.client.host if request.client else "unknown"
    if not limiter.allow(ip):
        raise HTTPException(status_code=429, detail=TOO_MANY)


# --------------------------------------------------------------------- schemas

Question = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]


class AskRequest(BaseModel):
    question: Question
    previous: Annotated[str, StringConstraints(strip_whitespace=True, max_length=500)] | None = None


class Source(BaseModel):
    n: int          # the number cited in the answer: [n]
    source: str     # readable title from documents_status.json ("titre"), or the file name if it has none
    file: str       # the file name in documents/
    page: int
    text: str


class AskResponse(BaseModel):
    answer: str
    sources: list[Source]
    corrected_query: str | None   # the question after typo/accent fixes; null when nothing changed


class FeedbackRequest(BaseModel):
    question: Question
    answer: Annotated[str, StringConstraints(min_length=1, max_length=20_000)]
    comment: Annotated[str, StringConstraints(strip_whitespace=True, max_length=2_000)] | None = None


class Health(BaseModel):
    status: str
    chunks: int
    model_loaded: bool


# ------------------------------------------------------------------- endpoints

def cited_numbers(answer, count):
    """The [n] numbers matching the sources returned by ask_with_context, in the same order.
    It keeps the cited numbers between 1 and len(selected), sorted: those are the smallest
    numbers >= 1, so the first `count` of them are exactly the ones it kept."""
    cited = sorted({int(n) for n in re.findall(r"\[(\d+)\]", answer)})
    return [n for n in cited if n >= 1][:count]


@app.get("/health", response_model=Health)
def health():
    bp = pipeline.get("build_prompt")
    return Health(
        status="ok" if bp else "loading",
        chunks=len(bp.chunks) if bp else 0,
        model_loaded=bool(bp and bp.model is not None),
    )


@app.post("/ask", response_model=AskResponse, dependencies=[Depends(rate_limited)])
def ask_endpoint(body: AskRequest):
    bp, ask, followup = pipeline["build_prompt"], pipeline["ask"], pipeline["followup"]
    titles = pipeline.get("titles", {})
    try:
        answer, sources = followup.ask_with_context(body.question, body.previous or None)
    except ask.GeminiUnavailable as e:
        raise HTTPException(status_code=503, detail=e.user_message)
    except Exception:
        logger.exception("ask_with_context failed for question %r", body.question)
        raise HTTPException(status_code=500, detail=INTERNAL_ERROR)

    corrected = bp.correct(bp.normalize(body.question))
    numbers = cited_numbers(answer, len(sources))
    return AskResponse(
        answer=answer,
        sources=[Source(n=n, source=titles.get(c["source"], c["source"]), file=c["source"],
                        page=c["page"], text=c["text"])
                 for n, c in zip(numbers, sources)],
        corrected_query=corrected if corrected != body.question else None,
    )


feedback_lock = threading.Lock()


@app.post("/feedback", status_code=201, dependencies=[Depends(rate_limited)])
def feedback(body: FeedbackRequest):
    line = {"timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"), **body.model_dump()}
    with feedback_lock, open(FEEDBACK_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(line, ensure_ascii=False) + "\n")
    return {"saved": True}
