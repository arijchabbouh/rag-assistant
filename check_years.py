import json
import re
from collections import Counter

# semesters 1-2 = first year, 3-4 = second year, 5-6 = third year
EXPECTED = {1: "première", 2: "première", 3: "deuxième",
            4: "deuxième", 5: "troisième", 6: "troisième"}

chunks = json.load(open("chunks.json", encoding="utf-8"))
counts = Counter()

for c in chunks:
    if not c["text"].startswith(("Plan d'études", "Liste des matières")):
        continue
    m = re.search(r"(\S+) année(?: — Option : (.+?))? — Semestre (\d+)", c["text"])
    if not m:
        counts[(c["source"], "NOT RECOGNIZED", "")] += 1
        continue
    year, option, sem = m.group(1), m.group(2), int(m.group(3))
    label = f"{year} année, semestre {sem}" + (f", option {option}" if option else "")
    flag = "" if EXPECTED.get(sem) == year else "  <-- CHECK"
    counts[(c["source"], label, flag)] += 1

for (source, label, flag), n in sorted(counts.items()):
    warn = "  <-- MANY" if n > 30 else ""
    print(f"{source} | {label} : {n}{flag}{warn}")