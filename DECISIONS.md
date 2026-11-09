# Decisions

One entry per design choice: what, why, what else was possible.

## Evaluation (2026-10-05)

**Metrics: hit@k and MRR, on retrieval only.**
hit@k says whether the right chunk reaches the LLM; MRR says how high it is ranked.
Alternatives: precision@k (needs every relevant chunk labelled, too costly by hand), nDCG (useful with
graded relevance; here a chunk is right or wrong), RAGAS (judges the written answer with an LLM: slower,
costs API calls, less reproducible). Chosen because they are free, deterministic, and run in seconds.

**Ground truth = file name + keywords that the right chunk must contain**, not chunk ids.
Chunk ids change every time the chunking changes; keywords survive a re-chunking.
Cost: a keyword that is too general accepts wrong chunks, so each keyword must be specific.
`evaluate.py` prints BAD KEYWORDS when no chunk can match.

**Questions are tagged by type** (direct, paraphrase, noisy, crosslingual).
The first 26 questions were close to the documents' wording and scored 100% hit@8: a test that everything
passes cannot show an improvement. The per-type table shows where retrieval is weak (paraphrases: 75% hit@8).

**The system never reads the eval set.**
`build_prompt.py` used to add the words of `eval_questions.json` to the typo-fix vocabulary, so eval
questions were never "corrected" while real questions were. Removed. Measured effect: MRR 0.802 → 0.796.

**Every measured change is one line in `results.md`** (`python evaluate.py "what changed"`).

## Calendar parsing fix (2026-10-09)

The month regex in `table_chunks.py` accepted "févr" and "avr" but the calendar writes "fev" and "avril",
so 6 calendar lines were silently dropped (492 → 498 chunks). Found by comparing the raw PDF text with
`chunks.json`, not by the eval: no question asked about those lines. Scores unchanged (MRR 0.796).
Lesson: the eval only measures what its questions cover; a parser also needs a "nothing was lost" check.

## Answer formatting (2026-10-09)

**The prompt asks for a Markdown table when the answer is a list of dates or a list of courses with several
attributes**, and for a plain sentence when the answer is one fact.
Alternative: build the table in Python from the retrieved chunks. Rejected for now: it needs structured
fields (date, event, coefficient...) and the chunks are plain sentences. Cost of the prompt approach: the
format is not guaranteed, the model decides.

## "List them all" questions (2026-10-09)

**A question detected as an enumeration ("toutes les dates", "liste des matières") gets 25 chunks instead of 8.**
Detection is a regex: an exhaustive wording followed by a generic plural noun. Normal questions keep 8,
because extra chunks are noise for a single-fact question.
Alternatives: always send 25 (worse answers on normal questions, more tokens); ask an LLM to classify the
question (one more API call per question); answer list questions from the structured data without retrieval
(the right long-term fix, needs structured chunks). The regex is cheap and its failure is safe: a missed
enumeration still gets rule 8 of the prompt, which adds "cette liste peut être incomplète".
Limit: the calendar has 50 lines, so even 25 chunks give a partial list.

## Document status: current vs archived (2026-10-09)

**`documents_status.json` marks each document "actuel" or "archive"; archived chunks are left out of the
search unless the question asks about the past** ("ancien", "avant", "archive", "précédent", "en 2017").
Why: the 2017 brochure describes three third-year specialities that the current study plan replaced with
a common core and three baskets of optional courses. Both were retrieved together and the model could
answer with the 2017 structure.
Why a JSON file and not the code: a non-developer can change a status without touching Python.
Alternatives: delete old documents (loses the ability to answer "how was it before"); let the LLM decide
from dates in the text (unreliable, most chunks carry no date); rank newer documents higher (a soft
preference still lets an old answer through).
In the eval, the 2 questions whose answer is in the brochure are searched with archives included.

## Typo fixer: never rewrite correct French (2026-11-09)

The old `correct()` "fixed" any word absent from the documents into the closest document word: on the
52 eval questions it changed 24 ("Quel" → "Que", "faut" → "fait", "menu" → "ment", "anciennes" → "antennes",
"noté" → "note"). A word is now left alone if it is:
1. a document word, or in `french_words.txt` (everyday words, edited by hand);
2. typed with accents: accents are only added to accent-less words ("delai" → "délai"), never changed;
3. another form of the candidate (same stem, plural/feminine/conjugation ending: "visitent" / "visites",
   "accordée" / "accorder").
Alternatives: only fix words of 5+ letters (would block "foum" → "forum" and still allow
"change" → "charge"); a full French dictionary (a large dependency or file for a small benefit).
`tests/test_correct.py`: 40 normal questions must come out unchanged, 13 real typos must be fixed.
Eval: hit@1 73% → 75%, MRR 0.796 → 0.804, hit@8 unchanged, noisy unchanged. hit@5 92% → 90%: "Le rapport
de PFE peut-il être confidentiel ?" goes from rank 5 to 7, because the old rule turned the French word
"confidentiel" into the English "confidential", which matched the English agreement by accident. Still in
the top 8 sent to the LLM. Not restored: translating is not a typo fix.
Lost on purpose: "infotronique" → "infotroniques" (singular/plural, left to the search model).

## Known weaknesses, not fixed yet

- A "list everything" question sees 25 chunks: "quelles sont toutes les dates du calendrier" returns 25
  dates out of 50, with the warning that the list may be incomplete. Still partial.
- "Quelles sont les options en 3ème année informatique" is refused. The current study plan never uses the
  word "option": the choice is made through three baskets (Panier SI / Rx / Emb), and the footnote that
  explains it ("choisir 6 matières optionnelles") is dropped by the table chunker.

- No unanswerable questions in the eval set: refusals are a generation behaviour, and generation is not
  evaluated yet.
- 52 questions: one question is about 2 points. Differences below ~4 points are noise.
