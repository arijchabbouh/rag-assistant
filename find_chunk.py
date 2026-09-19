import json
import sys

chunks = json.load(open("chunks.json", encoding="utf-8"))
keyword = sys.argv[1].lower()
matches = [c for c in chunks if keyword in c["text"].lower()]

print(f"{len(matches)} chunk(s) contain '{sys.argv[1]}'\n")
for c in matches[:3]:
    print(f'--- {c["source"]} (page {c["page"]}) ---')
    print(c["text"])
    print()
    