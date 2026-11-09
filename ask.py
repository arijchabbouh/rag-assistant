import config
import os
import re
import sys
import time

if not os.environ.get("GEMINI_API_KEY"):
    print("GEMINI_API_KEY is not set. Set your key first (see the instructions), then reopen the terminal.")
    raise SystemExit

from google import genai
from google.genai import types
from build_prompt import retrieve, build_prompt

# Models tried in this order. The free limits are counted PER MODEL, so when one is
# exhausted the next one can still answer. Names change: check them in Google AI Studio
# (a name that no longer exists is simply skipped).
# Order measured on 2026-11-09 (3 calls each, trivial prompt): flash-lite 0.6 / 6.6 / 13.5 s,
# 3.5-flash 5.8 / 12.0 / 18.2 s. gemini-3.8-flash removed: 504 DEADLINE_EXCEEDED after ~28 s, 3 times out of 3.
MODELS = ["gemini-3.1-flash-lite", "gemini-3.5-flash"]

# Without a timeout, a model that never answers blocks the question forever. After 30 s the call
# fails and generate() tries the next model.
TIMEOUT_MS = 30_000

client = genai.Client(http_options=types.HttpOptions(timeout=TIMEOUT_MS))  # key read from GEMINI_API_KEY


LIMIT_MESSAGE = (
    "La limite gratuite de Gemini est atteinte pour le moment. Attendez une minute puis réessayez. "
    "Si cela se répète, la limite du jour est peut-être épuisée : elle se remet à zéro "
    "vers 8h-9h du matin, heure de Tunis."
)
BUSY_MESSAGE = (
    "Les serveurs de Gemini sont momentanément surchargés ou indisponibles (le problème vient de Google, "
    "pas de votre code). Attendez une minute puis réessayez."
)


class GeminiUnavailable(Exception):
    """No model could answer: free limit reached, or Google's servers are busy."""
    def __init__(self, user_message):
        super().__init__(user_message)
        self.user_message = user_message


def is_rate_limit(error):
    text = f"{type(error).__name__} {error}"
    return getattr(error, "code", None) == 429 or "429" in text or "RESOURCE_EXHAUSTED" in text or "RateLimit" in text


def is_server_error(error):
    """Google's servers failed, or did not answer within TIMEOUT_MS (httpx.ReadTimeout, ConnectTimeout...)."""
    text = f"{type(error).__name__} {error}"
    return (getattr(error, "code", None) in (500, 502, 503, 504) or "ServerError" in text
            or "UNAVAILABLE" in text or "overloaded" in text.lower()
            or "timeout" in type(error).__name__.lower() or "timed out" in text.lower())


def is_missing_model(error):
    text = f"{error}".lower()
    return getattr(error, "code", None) == 404 or "not_found" in text or "not found" in text


def generate(prompt):
    """Ask Gemini. If a model is over its limit or busy, try the next one; if all fail, wait once and retry."""
    last_error = None
    for round_number in range(2):
        for model in MODELS:
            try:
                response = client.models.generate_content(model=model, contents=prompt)
                if model != MODELS[0]:
                    print(f"(modèle utilisé : {model})")
                return response.text or "Je n'ai pas pu générer de réponse."
            except Exception as e:
                if is_rate_limit(e) or is_server_error(e) or is_missing_model(e):
                    last_error = e
                    continue
                raise
        if round_number == 0:
            print("(Gemini est occupé ou limité, nouvelle tentative dans 20 s...)")
            time.sleep(20)
    raise GeminiUnavailable(LIMIT_MESSAGE if last_error and is_rate_limit(last_error) else BUSY_MESSAGE) from last_error


def ask(question):
    """Search the documents, ask the LLM, return (answer, cited_chunks)."""
    selected = retrieve(question)
    prompt = build_prompt(question, selected)
    answer = generate(prompt)

    cited = sorted({int(n) for n in re.findall(r"\[(\d+)\]", answer)})
    sources = [selected[n - 1] for n in cited if 1 <= n <= len(selected)]
    return answer, sources


if __name__ == "__main__":
    question = " ".join(sys.argv[1:])
    try:
        answer, sources = ask(question)
    except GeminiUnavailable as e:
        print("\n" + e.user_message)
        raise SystemExit
    print("\n" + answer + "\n")
    if sources:
        print("Sources :")
        for c in sources:
            print(f"  - {c['source']} (page {c['page']})")