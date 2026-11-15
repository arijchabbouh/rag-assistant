# ENICarthage documents assistant (RAG)

A chat assistant that answers students' questions from the school's official documents
(study plans, academic calendar, student guide, internship forms). Every answer **cites its source**
(file and page), and the assistant **refuses to answer** when the documents don't contain the information.

![The React interface answering with a table; citation [1] has opened its source, shown by its title](docs/screenshot.png)

## How it works

```
 PREPARATION (once, offline)
 ┌────────────┐   ┌──────────────────────────────┐   ┌──────────────────────┐
 │ documents/ │──▶│ chunk_documents.py           │──▶│ chunks.json          │
 │ PDF, DOCX  │   │ study plan → 1 line / course │   │ text, source, page,  │
 └────────────┘   │ calendar   → 1 line / event  │   │ status (actuel /     │
       ▲          │ guide      → 1 chunk/article │   │ archive)             │
       │          │ other      → 800-char pieces │   └──────────┬───────────┘
 documents_       └──────────────────────────────┘              │
 status.json                                         embed_chunks.py
 (actuel/archive)                                   (multilingual-e5-small)
                                                                ▼
                                                     ┌──────────────────────┐
                                                     │ embeddings.npy       │
                                                     │ 384 numbers / chunk  │
                                                     └──────────┬───────────┘
 EACH QUESTION (React → api.py, or app.py)                      │
 ┌──────────┐   ┌─────────────────────┐   ┌─────────────────────▼──────────┐
 │ question │──▶│ clean-up            │──▶│ retrieve (build_prompt.py)     │
 └──────────┘   │ CAPS, accents,      │   │ cosine similarity              │
                │ typos, CC/SR/PFE... │   │ 8 chunks, 25 for "list all"    │
                └─────────────────────┘   │ archived docs left out unless  │
                                          │ the question asks about the past│
                                          └─────────────────────┬──────────┘
                                                                ▼
 ┌─────────────────────────────┐   ┌──────────────────────────────────────┐
 │ answer + cited file / page  │◀──│ Gemini: rules + numbered excerpts    │
 │ (React or Streamlit chat)   │   │ "answer only from the excerpts, cite │
 └─────────────────────────────┘   │ [n], otherwise say you don't know"   │
                                   └──────────────────────────────────────┘
```

## Install and run (Windows, PowerShell)

The school documents are **not** included in the repository. Put your own PDFs in a `documents/` folder.
File names matter: study plans start with `PE_`, the calendar with `Calendrier`, the guide with `Guide_`
(any other file is cut into plain text pieces).

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1          # cmd.exe: .venv\Scripts\activate.bat
pip install -r requirements.txt

python chunk_documents.py           # documents/ -> chunks.json
python embed_chunks.py              # chunks.json -> embeddings.npy (downloads the model the first time)
```

If PowerShell refuses to run `Activate.ps1`, run once:
`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.

Get a free Gemini API key from Google AI Studio, then:

```powershell
Copy-Item .env.example .env
notepad .env                        # GEMINI_API_KEY=your_key
```

Then start **one** of the two interfaces.

**React interface (recommended)**: two terminals. Needs Node.js 20.19+ or 22.12+.

```powershell
# terminal 1, project folder, .venv activated
uvicorn api:app --port 8000

# terminal 2
cd frontend
npm install                         # first time only
npm run dev                         # opens http://localhost:5173
```

**Streamlit interface (older, kept for now)**: one terminal.

```powershell
streamlit run app.py                # opens http://localhost:8501
```

Command line, without the interface:

```powershell
python ask.py "quand est le forum des entreprises"
python build_prompt.py "ta question"   # shows the retrieved chunks, writes prompt.txt, no API call
python evaluate.py                     # retrieval scores, no API call
```

## HTTP API (FastAPI)

`api.py` exposes the same pipeline as the Streamlit app (`followup.ask_with_context`), for a web front end.

```powershell
uvicorn api:app --reload --port 8000
```

The embedding model and `embeddings.npy` are loaded once at startup. Interactive docs, where you can
also try each endpoint: http://localhost:8000/docs

| Method | Path | Body | Response |
|---|---|---|---|
| GET | `/health` | none | `{status, chunks, model_loaded}` |
| POST | `/ask` | `{question, previous}`: question 1 to 500 characters, `previous` = the student's last question or `null` | `{answer, sources: [{n, source, file, page, text}], corrected_query}` |
| POST | `/feedback` | `{question, answer, comment}` | `201 {saved: true}`. Adds a timestamped JSON line to `feedback.jsonl` (not in git) |

- `sources[].n` is the `[n]` number cited in the answer. Only the excerpts that the answer cites are returned.
- `sources[].source` is the document's readable title (`titre` in `documents_status.json`), or its file
  name when it has none; `sources[].file` is always the file name.
- `corrected_query` is the question after the CAPS/accent/typo fixes, or `null` if nothing changed.
- Errors: `422` invalid body, `429` more than 20 requests per minute from the same IP, `503` Gemini
  unavailable (limit reached or servers busy; `detail` is a French message to show to the student),
  `500` anything else (generic message; the details are only in the server logs).
- CORS: the allowed origins come from `ALLOWED_ORIGINS` in `.env`, comma-separated
  (default `http://localhost:5173`, the React dev server).

Example with curl (Git Bash). For questions with accents, prefer the `/docs` page: on Windows, accented
characters typed on the command line are not always sent as UTF-8, and the API then answers
`400 There was an error parsing the body`.

```bash
curl -X POST http://localhost:8000/ask -H "Content-Type: application/json" \
     -d '{"question": "quand est le forum des entreprises ?", "previous": null}'
```

```json
{"answer": "Le forum des entreprises a lieu le 17 novembre pour l'année universitaire 2026-2027 [1].",
 "sources": [{"n": 1, "source": "Calendrier_de_l'Année_Universitaire_26-27_1_1.pdf", "page": 1,
              "text": "Calendrier de l'année universitaire 26-27 — 17-nov Forum des entreprises"}],
 "corrected_query": null}
```

Tests (retrieval is real and needs `chunks.json` + `embeddings.npy`; Gemini is replaced by a fake):

```powershell
python -m pytest -q
```

## Web interface (React)

`frontend/` is a Vite + React app that calls the API. It never talks to Gemini directly.

- Chat with answers rendered as Markdown, including tables (`react-markdown` + `remark-gfm`).
- Citations `[n]` are buttons: they open source card n (document title, page, excerpt) and move the focus
  to it. Cards and citations show the document's `titre`; the file name is in the tooltip.
- **Arrêter** while an answer is being generated (`AbortController`), **Modifier** on the last question
  (puts it back in the input; sending replaces the last exchange), **Réessayer** after an error.
- Follow-ups: each request sends `previous`, the last question that got an answer.
- **Signaler une réponse fausse** under each answer, with an optional comment → `POST /feedback`.
- French error messages: 503 quota/busy (the API's own message), 429, 422, server unreachable.
- 5 example questions on the welcome screen, and a permanent "Vérifiez l'information officielle auprès
  de l'administration en cas de doute." notice.

Settings:

- **Colours**: CSS variables at the top of `frontend/src/styles.css` (`--primary: #8b1e3f` and its shades).
  Every text colour has a contrast of at least 6:1 with its background, and borders of interactive elements
  at least 3:1.
- **Logo**: `public/LOGO.jpg` at the project root (Vite's `publicDir` points to it, so there is only one copy).
- **API address**: `VITE_API_URL` (default `http://localhost:8000`); copy `frontend/.env.example` to
  `frontend/.env.local` to change it. The dev server always uses port 5173, the origin allowed by the
  API's `ALLOWED_ORIGINS`.

Checked on 2026-11-09 in headless Edge, with real Gemini answers. Desktop 1280 px and mobile 390 px:
suggestions, loading, citations (in text and in tables), source cards, Arrêter, Modifier, `previous` sent on
follow-ups, feedback, 503/429/network error messages (faked in the page), keyboard focus, no horizontal
scroll, no console error. These checks are not automated in the repository yet.

Production build: `npm run build` (output in `frontend/dist/`, not in git).

## Adding or archiving a document

`documents_status.json` says, for each file in `documents/`, how to show it and whether it is still in
force. It is edited by hand; no Python change is needed.

```json
"Plaquette_Dep_Informatique_2017.pdf": {
  "titre": "Plaquette du département Informatique (2017)",
  "status": "archive",
  "annee_scolaire": "2017",
  "note": "Describes 3rd-year specialities that no longer exist."
}
```

- `titre`: the name the student sees on source cards and citations, instead of the file name.
  Short and explicit: the kind of document, the programme, the year if it matters
  ("Calendrier universitaire 2026-2027", "Plan d'études Informatique", "Convention de stage PFE (anglais)").
  Optional: without it the file name is shown, and the API logs a warning at startup.
- `status`: `"actuel"` = used to answer. `"archive"` = left out of the search, **unless** the question asks
  about the past (`ancien`, `avant`, `archive`, `précédent`, `en 2017`...). When an archived excerpt is used,
  the answer says that it comes from an old document.

**Add a document:** copy the file into `documents/`, add an entry in `documents_status.json` with its
`titre` and `status` (copy an existing entry and keep the file name as the key, exactly), then run
`python chunk_documents.py` and `python embed_chunks.py`.
A file missing from `documents_status.json` is treated as `actuel` and a warning is printed.

**Archive a document** (for example when next year's calendar arrives): change its `status` to
`"archive"` and run `python chunk_documents.py`, then `python embed_chunks.py`.

**Rename a document for students:** change its `titre`, then restart the API. Nothing to re-run.

Restart the API (or the Streamlit app) after any change: everything is loaded once at startup.
The Streamlit app still shows file names.

## Evaluation results

Test set: 62 questions written by hand (`eval_questions.json`). For each question, the file and the text
that the right chunk must contain. Four types: `direct` (close to the document's wording), `paraphrase`,
`noisy` (abbreviations, no accents, fragments such as "forum entreprises date"), `crosslingual` (question and document in different languages).

- **hit@k**: the right chunk is among the first k results.
- **MRR**: average of 1/rank of the right chunk (1 = always first).

Latest run (2026-11-15, retrieval only, the top 8 chunks go to the LLM):

| Type | Questions | hit@1 | hit@3 | hit@5 | hit@8 | MRR |
|---|---|---|---|---|---|---|
| direct | 26 | 85% | 96% | 100% | 100% | 0.901 |
| paraphrase | 16 | 69% | 75% | 75% | 75% | 0.708 |
| noisy | 17 | 71% | 82% | 88% | 88% | 0.770 |
| crosslingual | 3 | 33% | 67% | 67% | 100% | 0.492 |
| **all** | **62** | **74%** | **85%** | **89%** | **90%** | **0.795** |

Every measured change is one line in [results.md](results.md) (`python evaluate.py "what changed"`).
Design choices and the alternatives considered are in [DECISIONS.md](DECISIONS.md).

The test set is small: one question is about 2 points, so these numbers show a trend, not a guarantee.

## Known limits

- **Answers can be wrong.** Always check the cited source.
- **Only retrieval is evaluated.** The answers written by the LLM, including refusals, are not scored yet.
- **Paraphrases are the weak spot:** 4 of 16 reworded questions never get the right chunk in the top 8.
- **A refused question gets one more try**: the model rewrites it as a clear question, the search runs
  again, the model answers again (two more Gemini calls, only on refusals). A second refusal is kept, with
  "Essayez de reformuler votre question avec plus de détails (filière, année)." It does not always help:
  on 2026-11-15 it recovered "PFE durée minimum" once out of two runs, and never "Le rapport de PFE
  confidentiel ?" (the answer is in the English agreement, rank 26 for the rewritten question).
- **"List everything" questions are partial.** They get 25 chunks, but the calendar alone has 50 lines:
  "toutes les dates du calendrier" returns part of them, with a warning that the list may be incomplete.
- **Vocabulary mismatch is fixed by hand, word by word.** Students say "options", the Informatique study
  plan says "panier d'option" / "matières optionnelles": `SYNONYMS` in `build_prompt.py` adds the documents'
  words to the search and tells the model about them. Other student words may still miss.
  "Les options en 3ème année informatique" now gets an answer, but the list of courses is partial
  (13 of the 28 basket courses reach the model), and the model may expand "SI / Rx / Emb" from its own
  knowledge.
- **The typo fixer only knows the documents' words and a hand-made list** (`french_words.txt`). A correct
  French word that is in neither list and is one letter away from a document word can still be "fixed":
  add it to `french_words.txt`. Tested on 40 normal questions (`tests/test_correct.py`).
- **Gemini answer time varies a lot** (0.6 to 18 s for a trivial prompt on 2026-11-09). Each model gets
  30 s (`ask.TIMEOUT_MS`), then the next one is tried. The faster model is first, a "lite" one: its
  answers are not evaluated yet.
- **API rate limit is in memory, per process:** it resets on restart, is not shared between several
  uvicorn workers, and behind a reverse proxy every client has the proxy's IP.
- **Archive detection is a word list.** A question about the past without one of those words won't see
  archived documents; a current question containing "avant" will.
- **No OCR:** scanned PDFs are not read.
- **Short memory:** the chat only remembers the previous question, and the React page keeps nothing
  after a reload.
- **Arrêter only stops the waiting.** The server finishes its Gemini call anyway, so a stopped question
  still uses the free quota.
- **Free Gemini tier:** rate limits. The app tries several models in turn and shows a clear message
  when all are busy.
- **Parsers depend on file names and layouts** (`PE_`, `Calendrier`, `Guide_`). A new layout may need
  changes in `table_chunks.py` or `article_chunks.py`.

## Files

```
app.py                 Streamlit chat interface (older; the React one replaces it)
frontend/              React interface (Vite): src/App.jsx, src/components/, src/styles.css, src/api.js
api.py                 FastAPI: /ask, /health, /feedback (CORS, rate limit, error mapping)
tests/                 pytest: API (Gemini faked), model fallback, typo fixer, synonyms
ask.py                 retrieval + Gemini call, model fallback, CLI entry point
build_prompt.py        query clean-up, retrieval, enumeration/archive detection, prompt rules
followup.py            merges the previous question for follow-ups ("et en 2ème année ?")
suggestions.py         question suggestions shown while the student types
config.py              reads .env
french_words.txt       everyday words the typo fixer must never change (edited by hand)

chunk_documents.py     documents/ -> chunks.json (uses documents_status.json)
table_chunks.py        study-plan tables (+ their footnotes) and calendar parsers (pdfplumber)
article_chunks.py      student guide: one chunk per article
embed_chunks.py        chunks.json -> embeddings.npy
documents_status.json  actuel / archive for each document (edited by hand)

evaluate.py            hit@k and MRR on eval_questions.json, appends to results.md
eval_questions.json    62 hand-written test questions
add_question.py        helper to add a test question
results.md             history of every measured change
DECISIONS.md           design choices, alternatives, known weaknesses

debug_question.py, why.py, search.py, find_chunk.py, show_chunk.py, show_source.py,
show_page.py, test_tables.py, check_documents.py, check_years.py, list_semesters.py
                       small debugging tools (inspect chunks, pages, retrieval)

.streamlit/config.toml interface theme
public/LOGO.jpg        logo shown in both interfaces
docs/screenshot.png    README screenshot
.env.example           template for .env (the real .env is never committed)

Not in git: documents/, chunks.json, embeddings.npy, feedback.jsonl, .env, .venv/,
            frontend/node_modules/, frontend/dist/
```

## Stack

Python 3.10, pypdf, pdfplumber, python-docx, sentence-transformers (`intfloat/multilingual-e5-small`),
NumPy, Google Gemini API, FastAPI + uvicorn, pytest, React 19 + Vite (react-markdown, remark-gfm),
Streamlit.
