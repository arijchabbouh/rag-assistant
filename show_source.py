import json
import sys

chunks = json.load(open("chunks.json", encoding="utf-8"))
keyword = sys.argv[1].lower()

for c in chunks:
    if keyword in c["source"].lower():
        text = c["text"].replace("Calendrier de l'année universitaire 26-27 — ", "")
        print(f"[page {c['page']}] {text}")
        print()