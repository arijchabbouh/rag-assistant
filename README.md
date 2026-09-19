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

Test set: questions written by hand from the documents. Metric: the chunk containing the answer
is among the chunks given to the LLM.

| Version | Recall@5 | Right chunk ranked first |
|---|---|---|
| v1: guide cut in fixed-size pieces | 10/11 | 8/11 |
| v2: guide cut by article | 11/11 | 8/11 |
| TODO: latest run (number of questions, Recall@8) | | |

TODO: paste the table printed by `python stress_test.py` (typing patterns, with and without fixes).

Small test set: these numbers show a trend, not a guarantee.

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