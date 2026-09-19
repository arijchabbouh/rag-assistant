import json
import sys
import numpy as np
from sentence_transformers import SentenceTransformer

MODEL_NAME = "intfloat/multilingual-e5-small"

chunks = json.load(open("chunks.json", encoding="utf-8"))
embeddings = np.load("embeddings.npy")
model = SentenceTransformer(MODEL_NAME)

question = " ".join(sys.argv[1:])
# ...and the prefix "query: " on questions
q = model.encode(["query: " + question], normalize_embeddings=True)[0]

scores = embeddings @ q                    # similarity with every chunk
top = np.argsort(scores)[::-1][:5]         # the 5 best

for i in top:
    c = chunks[i]
    print(f"[{scores[i]:.3f}] {c['source']} (page {c['page']})")
    print(c["text"][:300])
    print()