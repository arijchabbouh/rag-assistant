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


def generate(prompt, temperature=None):
    """Ask Gemini. If a model is over its limit or busy, try the next one; if all fail, wait once and retry.
    temperature=0 gives (almost) the same text every time: used to rephrase questions."""
    config = types.GenerateContentConfig(temperature=temperature) if temperature is not None else None
    last_error = None
    for round_number in range(2):
        for model in MODELS:
            try:
                response = client.models.generate_content(model=model, contents=prompt, config=config)
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


# ------------------------------------------------------------- refusals: one more try

REFUSAL = "Je ne trouve pas cette information dans les documents fournis."   # rule 3 of the prompt
REPHRASE_HINT = "Essayez de reformuler votre question avec plus de détails (filière, année)."

REPHRASE_PROMPT = """Un étudiant de l'École Nationale d'Ingénieurs de Carthage a posé la question ci-dessous \
à un assistant qui cherche dans les documents officiels de l'école. Elle est peut-être fragmentaire, abrégée \
ou mal tournée.
Réécris-la en UNE question claire, complète et autonome, en français : une phrase entière, des mots complets, \
sans fautes. Si l'étudiant a écrit un sigle de l'école (PFE, PFA, CC, DS, SP, SR, UE), garde-le tel quel : \
la recherche le connaît. N'ajoute pas de sigle qu'il n'a pas écrit.\
{context}
Garde le sens exact et les mots de l'étudiant : ajoute seulement ce qui manque pour faire une phrase (verbe, \
article, mot interrogatif). Ne suppose rien de plus que la question.
N'ajoute aucune information absente de la question : pas de filière, d'année, de date ni de chiffre inventés, \
et pas le nom de l'école. Reste courte.
Exemples :
« stage ete duree ? » -> Quelle est la durée du stage d'été ?
« bourse demande ou » -> Où faut-il faire une demande de bourse ?
Réponds uniquement par la question réécrite, sans guillemets ni explication.

Question : {question}"""


def is_refusal(answer):
    """True when the model answered with the refusal sentence (possibly followed by a comment)."""
    return answer.strip().lstrip("«\"' ").startswith(REFUSAL[:34])   # "Je ne trouve pas cette information"


def rephrase(question, previous=None):
    """Ask the model for a clear, self-contained version of the question. Returns the question unchanged
    if the model gives nothing usable."""
    context = (f"\nElle suit peut-être la question précédente de l'étudiant : « {previous} ». "
               f"Si c'est le cas, intègre ce contexte pour que la question se comprenne seule.") if previous else ""
    text = generate(REPHRASE_PROMPT.format(question=question, context=context), temperature=0).strip()
    text = text.splitlines()[0].strip().strip("«»\"' ") if text else ""
    return text if 0 < len(text) <= 500 else question


def cited_sources(answer, selected):
    """The chunks cited as [n] in the answer."""
    cited = sorted({int(n) for n in re.findall(r"\[(\d+)\]", answer)})
    return [selected[n - 1] for n in cited if 1 <= n <= len(selected)]


def retry_after_refusal(question, answer, selected, previous=None):
    """A refused question gets ONE more try: the model rewrites it as a clear question, the search runs again
    on the rewritten question, and the model answers again. A second refusal is kept, with a hint.
    Costs nothing for answered questions, two more calls for refused ones. Returns (answer, selected)."""
    if not is_refusal(answer):
        return answer, selected
    try:
        clear = rephrase(question, previous)
        if clear.strip().lower() != question.strip().lower():
            retried = retrieve(clear)
            answer2 = generate(build_prompt(f"{clear}\n(Question posée par l'étudiant : « {question} ».)", retried))
            if not is_refusal(answer2):
                return answer2, retried
    except GeminiUnavailable:
        pass    # no second chance right now: keep the first refusal
    return f"{answer.strip()}\n\n{REPHRASE_HINT}", selected


def ask(question):
    """Search the documents, ask the LLM, return (answer, cited_chunks)."""
    selected = retrieve(question)
    answer = generate(build_prompt(question, selected))
    answer, selected = retry_after_refusal(question, answer, selected)
    return answer, cited_sources(answer, selected)


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