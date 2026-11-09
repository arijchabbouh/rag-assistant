import json
import re
import sys
import unicodedata
from collections import Counter

import numpy as np
from sentence_transformers import SentenceTransformer

MODEL_NAME = "intfloat/multilingual-e5-small"
TOP_K = 8          # chunks given to the LLM for a normal question
TOP_K_ENUM = 25    # ...for a "list them all" question (see is_enumeration)

chunks = json.load(open("chunks.json", encoding="utf-8"))
embeddings = np.load("embeddings.npy")
model = SentenceTransformer(MODEL_NAME)
# True for the chunks of a document marked "archive" in documents_status.json
ARCHIVED = np.array([c.get("status") == "archive" for c in chunks])


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
6. Abréviations courantes : CC = contrôle continu ; DS = devoir surveillé ; SP = session principale ; SR = session de rattrapage ; PFE = projet de fin d'études ; UE = unité d'enseignement.
7. Mise en forme : si la réponse est une liste de plusieurs dates ou événements (calendrier), ou une liste de plusieurs matières avec plusieurs attributs (coefficient, volume horaire, évaluation...), présente-la dans un tableau Markdown : une ligne par événement ou par matière, une colonne par attribut, et la source [n] dans la dernière colonne. Si la réponse tient en une seule information, réponds par une phrase, sans tableau.
8. Si la question demande une liste complète (toutes les dates, toutes les matières, tous les examens...), donne tous les éléments présents dans les extraits, puis termine par cette phrase exacte : « Attention : cette liste peut être incomplète, vérifiez le document source. » Seule exception : quand tous les éléments viennent d'un seul extrait qui est lui-même une liste (par exemple un extrait « Liste des matières »).
9. Un extrait marqué « DOCUMENT ARCHIVÉ » décrit une situation ancienne, qui n'est peut-être plus valable. Si tu l'utilises, dis clairement dans la réponse que l'information vient d'un ancien document."""


def strip_accents(text):
    return "".join(c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn")


EXTRA_WORDS = """pourcentage combien quelle quelles quels quand comment pourquoi durée limite
dernier dernière délai inscription examen examens moyenne moyennes crédits crédit coefficient
absence absences rattrapage session sessions stage stages projet soutenance soutenances rapport
dépôt calendrier règlement diplôme classement semestre année années matière matières cours
heures volume horaire obligatoire autorisé tolérées tolérée nombre maximum minimum date dates
étudiant étudiants élève élèves ingénieur département option formation""".split()

WORD_COUNTS = Counter(w for c in chunks for w in re.findall(r"[^\W\d_]{2,}", c["text"].lower()))
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


# Everyday French words that are never "corrected" (the documents don't contain all of them: "quel", "menu"...).
# Edited by hand in french_words.txt.
COMMON_WORDS = {
    w for line in open("french_words.txt", encoding="utf-8") if not line.lstrip().startswith("#")
    for w in re.findall(r"[^\W\d_]+", line.lower())
}

# Endings of plural, feminine and conjugated forms. Two words that differ only by these endings are two forms
# of the same word ("visitent" / "visites", "accordée" / "accorder", "langue" / "langues"): the student's form
# is kept, the search model handles it.
INFLECTIONS = ("", "s", "x", "e", "es", "é", "ée", "és", "ées", "er", "ez", "ent", "ant", "ants", "ante", "antes",
               "ons", "ait", "ais", "aient")
INFLECTIONS_PLAIN = sorted({strip_accents(s) for s in INFLECTIONS}, key=len, reverse=True)


def same_word_other_form(a, b):
    """True if a and b (without accents) are the same stem with two different endings: "visitent" / "visites"."""
    if a == b:              # only the accents differ ("delai" / "délai"): a real fix, not another form
        return False
    for ending in INFLECTIONS_PLAIN:
        if a.endswith(ending):
            stem = a[: len(a) - len(ending)]
            if len(stem) >= 3 and b.startswith(stem) and b[len(stem):] in INFLECTIONS_PLAIN:
                return True
    return False


def correct(question):
    """Fix missing accents and small typos, using the words found in the documents.
    Never touches a word that is already correct French: a document word, a common word (french_words.txt),
    a word typed with accents (only accent-less words get accents), or another form of the candidate word."""
    def fix_word(match):
        word = match.group(0)
        low = word.lower()
        if len(low) < 3 or low in WORD_COUNTS or low in ABBREVIATIONS or low in COMMON_WORDS:
            return word
        if word.isupper() and len(word) <= 5:      # probably an acronym (GSIL, INFO...)
            return word
        plain = strip_accents(low)
        # same letters, other accents: only when the student typed no accent at all ("delai" -> "délai");
        # a word typed with accents ("noté") is taken as written
        best = BY_PLAIN.get(plain) if plain == low else None
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
        if same_word_other_form(plain, strip_accents(best)):
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


# ----------------------------------------------------------------- enumeration

# "list them all" questions: an exhaustive wording followed by a generic plural noun.
# Checked on the question without accents, in lowercase.
ENUM_STARTS = (r"(?:tou(?:te)?s les|liste (?:complete )?(?:des|de toutes les|de tous les)|l.ensemble des"
               r"|quel(?:le)?s sont (?:toutes les|tous les|les))")
ENUM_NOUNS = (r"(?:dates?|evenements?|echeances?|delais?|matieres?|cours|modules?|options?|specialites?"
              r"|filieres?|examens?|soutenances?|stages?|unites? d.enseignement|ue)")
ENUMERATION = re.compile(rf"(?<!\w){ENUM_STARTS}\s+(?:\w+\s+)?{ENUM_NOUNS}(?!\w)")


def is_enumeration(question):
    """True for a question that asks for a whole list ("toutes les dates", "liste des matières")."""
    return bool(ENUMERATION.search(strip_accents(question.lower())))


def top_k_for(question):
    """How many chunks to give the LLM: more for a "list them all" question, which needs many lines."""
    return TOP_K_ENUM if is_enumeration(question) else TOP_K


# --------------------------------------------------------------------- archives

# The question asks about the past: "ancien", "avant", "archive", "précédent", or a year ("en 2017").
# Checked on the question without accents, in lowercase.
ARCHIVE_WORDS = re.compile(r"(?<!\w)(?:ancien(?:ne)?s?|avant|archives?|precedente?s?|en (?:19|20)\d\d)(?!\w)")


def wants_archive(question):
    """True when the question explicitly asks about old documents."""
    return bool(ARCHIVE_WORDS.search(strip_accents(question.lower())))


# ---------------------------------------------------------------------- search

def retrieve(question, k=None, fix=True, include_archive=None):
    """Return the k chunks closest in meaning to the question (k chosen from the question if not given).
    Chunks of archived documents are left out, unless the question asks about the past."""
    if k is None:
        k = top_k_for(question)
    if include_archive is None:
        include_archive = wants_archive(question)
    vec = model.encode(["query: " + expand(question, fix)], normalize_embeddings=True)[0]
    scores = embeddings @ vec
    if not include_archive:
        scores[ARCHIVED] = -1.0     # lower than any real similarity: archived chunks go last
    return [chunks[i] for i in np.argsort(scores)[::-1][:k]]


def build_prompt(question, selected):
    excerpts = "\n\n".join(
        f"[{n}] ({c['source']}, page {c['page']}"
        f"{', DOCUMENT ARCHIVÉ' if c.get('status') == 'archive' else ''})\n{c['text']}"
        for n, c in enumerate(selected, start=1)
    )
    return f"{RULES}\n\nEXTRAITS :\n\n{excerpts}\n\nQUESTION : {question}\n\nRÉPONSE :"


if __name__ == "__main__":
    question = " ".join(sys.argv[1:])
    selected = retrieve(question)
    with open("prompt.txt", "w", encoding="utf-8") as f:
        f.write(build_prompt(question, selected))
    print("Search used:", expand(question))
    print("Enumeration question:", is_enumeration(question), f"-> {len(selected)} chunks")
    print("Prompt saved to prompt.txt. Sources retrieved:")
    for n, c in enumerate(selected, start=1):
        print(f"  [{n}] {c['source']} (page {c['page']})")