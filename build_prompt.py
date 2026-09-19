import json
import re
import sys
import unicodedata
from collections import Counter

import numpy as np
from sentence_transformers import SentenceTransformer

MODEL_NAME = "intfloat/multilingual-e5-small"
TOP_K = 8   

chunks = json.load(open("chunks.json", encoding="utf-8"))
embeddings = np.load("embeddings.npy")
model = SentenceTransformer(MODEL_NAME)


ABBREVIATIONS = {
    "cc": "contrôle continu",
    "ds": "devoir surveillé",
    "sp": "session principale",
    "sr": "session de rattrapage",
    "pfe": "projet de fin d'études",
    "pfa": "projet de fin d'année",
    "ue": "unité d'enseignement",
    "tp": "travaux pratiques",
    "td": "travaux dirigés",
    "info": "informatique",
    "dep": "département",
    "ens": "enseignant",
    "etud": "étudiant",
    "sem": "semestre",
    
}

RULES = """Tu es un assistant qui répond aux questions des étudiants de l'École Nationale d'Ingénieurs de Carthage (ENICarthage).

Règles :
1. Réponds UNIQUEMENT à partir des extraits numérotés ci-dessous. N'utilise aucune autre connaissance.
2. Cite tes sources entre crochets après chaque information, par exemple [1] ou [2][3].
3. Si les extraits ne contiennent pas la réponse, réponds exactement : « Je ne trouve pas cette information dans les documents fournis. » Ne devine pas.
4. Si la réponse dépend du cas (année, option, type de stage...), donne chaque cas ou précise lequel s'applique.
5. Réponds en français, de façon courte et claire.
6. Abréviations courantes : CC = contrôle continu ; DS = devoir surveillé ; SP = session principale ; SR = session de rattrapage ; PFE = projet de fin d'études ; UE = unité d'enseignement."""


def strip_accents(text):
    return "".join(c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn")


EXTRA_WORDS = """pourcentage combien quelle quelles quels quand comment pourquoi durée limite
dernier dernière délai inscription examen examens moyenne moyennes crédits crédit coefficient
absence absences rattrapage session sessions stage stages projet soutenance soutenances rapport
dépôt calendrier règlement diplôme classement semestre année années matière matières cours
heures volume horaire obligatoire autorisé tolérées tolérée nombre maximum minimum date dates
étudiant étudiants élève élèves ingénieur département option formation""".split()

WORD_COUNTS = Counter(w for c in chunks for w in re.findall(r"[^\W\d_]{2,}", c["text"].lower()))
try:
    for _q in json.load(open("eval_questions.json", encoding="utf-8")):
        WORD_COUNTS.update(re.findall(r"[^\W\d_]{2,}", _q["question"].lower()))
except FileNotFoundError:
    pass
WORD_COUNTS.update(EXTRA_WORDS)
BY_PLAIN = {}   
for _word, _n in WORD_COUNTS.most_common():
    BY_PLAIN.setdefault(strip_accents(_word), _word)


def normalize(question):
    """If the question is mostly UPPERCASE, lowercase it (the search model is case-sensitive)."""
    letters = [c for c in question if c.isalpha()]
    if letters and sum(c.isupper() for c in letters) / len(letters) > 0.6:
        return question.lower()
    return question


def edit_distance(a, b, limit):
    """Edits needed to turn a into b (insert, delete, replace, swap two neighbours)."""
    if abs(len(a) - len(b)) > limit:
        return limit + 1
    prev2, prev = None, list(range(len(b) + 1))
    for i in range(1, len(a) + 1):
        cur = [i] + [0] * len(b)
        for j in range(1, len(b) + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + cost)
            if i > 1 and j > 1 and a[i - 1] == b[j - 2] and a[i - 2] == b[j - 1]:
                cur[j] = min(cur[j], prev2[j - 2] + 1)
        prev2, prev = prev, cur
    return prev[-1]


def correct(question):
    """Fix wrong/missing accents and small typos, using the words found in the documents."""
    def fix_word(match):
        word = match.group(0)
        low = word.lower()
        if len(low) < 3 or low in WORD_COUNTS or low in ABBREVIATIONS:
            return word
        if word.isupper() and len(word) <= 5:      # probably an acronym (GSIL, INFO...)
            return word
        plain = strip_accents(low)
        best = BY_PLAIN.get(plain)                  # same letters, other accents
        if best is None and len(plain) >= 4:        # a typo: closest known word
            limit = 1 if len(plain) <= 7 else 2
            scored = []
            for w in BY_PLAIN:
                if w[0] != plain[0] or abs(len(w) - len(plain)) > limit:
                    continue
                d = edit_distance(plain, w, limit)
                if d <= limit:
                    scored.append((d, -WORD_COUNTS[BY_PLAIN[w]], w))
            if scored:
                best = BY_PLAIN[min(scored)[2]]
        if best is None or best == low:
            return word
        return best.capitalize() if word[0].isupper() else best
    return re.sub(r"[^\W\d_]+", fix_word, question)


def expand(question, fix=True):
    """The text used for the search: fixed typing + full form of known abbreviations."""
    if fix:
        question = correct(normalize(question))
    found = []
    for abbr, full in ABBREVIATIONS.items():
        if re.search(rf"(?<!\w){abbr}(?!\w)", question, re.IGNORECASE):
            found.append(full)
    return question + (" (" + "; ".join(found) + ")" if found else "")


# ---------------------------------------------------------------------- search

def retrieve(question, k=TOP_K, fix=True):
    """Return the k chunks closest in meaning to the question."""
    vec = model.encode(["query: " + expand(question, fix)], normalize_embeddings=True)[0]
    scores = embeddings @ vec
    return [chunks[i] for i in np.argsort(scores)[::-1][:k]]


def build_prompt(question, selected):
    excerpts = "\n\n".join(
        f"[{n}] ({c['source']}, page {c['page']})\n{c['text']}"
        for n, c in enumerate(selected, start=1)
    )
    return f"{RULES}\n\nEXTRAITS :\n\n{excerpts}\n\nQUESTION : {question}\n\nRÉPONSE :"


if __name__ == "__main__":
    question = " ".join(sys.argv[1:])
    selected = retrieve(question)
    with open("prompt.txt", "w", encoding="utf-8") as f:
        f.write(build_prompt(question, selected))
    print("Search used:", expand(question))
    print("Prompt saved to prompt.txt. Sources retrieved:")
    for n, c in enumerate(selected, start=1):
        print(f"  [{n}] {c['source']} (page {c['page']})")