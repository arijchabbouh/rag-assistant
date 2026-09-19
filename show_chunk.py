import json
import sys

chunks = json.load(open("chunks.json", encoding="utf-8"))
keyword = sys.argv[1].lower()
matches = [c for c in chunks if keyword in c["source"].lower()]

for c in matches[1:3]:
    print(f'--- {c["source"]} (page {c["page"]}) ---')
    print(c["text"])
    print()