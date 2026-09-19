import sys
from build_prompt import retrieve, expand

question = " ".join(sys.argv[1:])
print("Search used:", expand(question), "\n")
for n, c in enumerate(retrieve(question), start=1):
    preview = c["text"][:110].replace("\n", " ")
    print(f"[{n}] {c['source']} (page {c['page']}): {preview}")