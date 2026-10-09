# ENICarthage documents assistant (RAG)

A chat assistant that answers students' questions from the school's official documents
(study plans, academic calendar, student guide, internship forms), **cites its sources**,
and **refuses to answer** when the documents don't contain the information.

TODO: add a screenshot of the app answering a question, and one showing a refusal.

## How it works

1. **Preparation (once):** PDFs are read and cut into chunks. Study-plan tables become one sentence per course,
   the calendar one line per event, the student guide one chunk per article. Each chunk is turned into
   384 numbers (embeddings, `multilingual-e5-small`).
2. **Each question:** typing fixes (CAPS, accents, small typos, abbreviations such as CC or SR) →
   the 8 closest chunks are found → a prompt with rules + numbered excerpts goes to Gemini →
   the answer is displayed with the cited file, page and line.

## Results

Test set: 52 questions written by hand (`eval_questions.json`), each with the file and the text that the
right chunk must contain. Four types: `direct` (close to the document's wording), `paraphrase`,
`noisy` (abbreviations, no accents), `crosslingual` (question and document in different languages).

- **hit@k**: the right chunk is among the first k results.
- **MRR**: average of 1/rank of the right chunk (1 = always first).

Latest run (retrieval only, top 8 chunks go to the LLM):

| Type | Questions | hit@1 | hit@3 | hit@5 | hit@8 | MRR |
|---|---|---|---|---|---|---|
| direct | 26 | 85% | 96% | 100% | 100% | 0.901 |
| paraphrase | 16 | 62% | 75% | 75% | 75% | 0.677 |
| noisy | 7 | 71% | 86% | 100% | 100% | 0.798 |
| crosslingual | 3 | 33% | 67% | 100% | 100% | 0.511 |
| **all** | **52** | **73%** | **87%** | **92%** | **92%** | **0.796** |

History of every measured change: [results.md](results.md). Reproduce with `python evaluate.py`.

Small test set: one question is about 2 points, so these numbers show a trend, not a guarantee.
The answers written by the LLM are not evaluated yet.

## Run it yourself

The school documents are not included. Put your own PDFs in a `documents/` folder.
File names matter: study plans start with `PE_`, the calendar with `Calendrier`, the guide with `Guide_`.

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python chunk_documents.py
python embed_chunks.py
```

Copy `.env.example` to `.env` and put your Gemini API key in it (free tier from Google AI Studio), then:

```
streamlit run app.py
```

## Known limits

- Answers can be wrong: always check the cited source.
- Only the documents provided are known. Scanned PDFs are not read (no OCR yet).
- The chat remembers only the previous question.
- The free Gemini tier has rate limits; the app tries several models and shows a clear message.

## Stack

Python, pypdf, pdfplumber, sentence-transformers, Google Gemini API, Streamlit.