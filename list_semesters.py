import json
import sys

chunks = json.load(open("chunks.json", encoding="utf-8"))
keyword = sys.argv[1].lower()

for c in chunks:
    if c["text"].startswith("Liste des matières") and keyword in (c["source"] + " " + c["text"]).lower():
        print(f'{c["source"]} (page {c["page"]})')
        print(c["text"])
        print()