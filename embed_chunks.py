import json
import numpy as np
from sentence_transformers import SentenceTransformer

MODEL_NAME = "intfloat/multilingual-e5-small"

chunks = json.load(open("chunks.json", encoding="utf-8"))
model = SentenceTransformer(MODEL_NAME)

# this model expects the prefix "passage: " on documents
texts = ["passage: " + c["text"] for c in chunks]
embeddings = model.encode(texts, batch_size=32,
                          normalize_embeddings=True, show_progress_bar=True)

np.save("embeddings.npy", embeddings)
print("Shape:", embeddings.shape)