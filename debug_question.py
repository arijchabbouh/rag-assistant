import json
import sys
import numpy as np
from sentence_transformers import SentenceTransformer

MODEL_NAME = "intfloat/multilingual-e5-small"

chunks = json.load(open("chunks.json", encoding="utf-8"))
embeddings = np.load("embeddings.npy")
questions = json.load(open("eval_questions.json", encoding="utf-8"))
model = SentenceTransformer(MODEL_NAME)

needle = " ".join(sys.argv[1:]).lower()
q = next((x for x in questions if needle in x["question"].lower()), None)
if q is None:
    print("No question contains that text.")
    raise SystemExit


def is_correct(chunk, q):
    if q["source"].lower() not in chunk["source"].lower():
        return False
    text = chunk["text"].lower()
    return all(k.lower() in text for k in q["keywords"])


vec = model.encode(["query: " + q["question"]], normalize_embeddings=True)[0]
scores = embeddings @ vec
order = np.argsort(scores)[::-1]

print("QUESTION:", q["question"])
print("EXPECTED: file contains", q["source"], "| keywords", q["keywords"])

print("\n--- top 5 returned ---")
for pos, i in enumerate(order[:5], start=1):
    mark = "   <== EXPECTED" if is_correct(chunks[i], q) else ""
    print(f"{pos}. [{scores[i]:.3f}] {chunks[i]['source']} (page {chunks[i]['page']}){mark}")
    print("   ", chunks[i]["text"][:200].replace("\n", " "))

print("\n--- the expected chunk ---")
for pos, i in enumerate(order, start=1):
    if is_correct(chunks[i], q):
        print(f"best-ranked expected chunk: rank {pos} of {len(chunks)}  [{scores[i]:.3f}]")
        print(f"{chunks[i]['source']} (page {chunks[i]['page']}):")
        print(chunks[i]["text"][:500])
        break
else:
    print("No chunk matches this question's source and keywords.")