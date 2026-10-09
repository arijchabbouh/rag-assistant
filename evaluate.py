import json
import sys
from datetime import date
from pathlib import Path

from build_prompt import retrieve, chunks, TOP_K, TOP_K_ENUM, is_enumeration

# usage: python evaluate.py                 -> print the metrics
#        python evaluate.py "what changed"  -> also add a line to results.md

KS = (1, 3, 5, TOP_K)
RESULTS = Path("results.md")

questions = json.load(open("eval_questions.json", encoding="utf-8"))


def is_correct(chunk, q):
    """Correct = right file AND all the keywords appear in the chunk."""
    if q["source"].lower() not in chunk["source"].lower():
        return False
    text = chunk["text"].lower()
    return all(k.lower() in text for k in q["keywords"])


def metrics(ranks):
    """ranks = position of the first correct chunk for each question (None = not retrieved)."""
    n = len(ranks)
    hits = {k: sum(1 for r in ranks if r and r <= k) / n for k in KS}
    # MRR: 1 point if the right chunk is first, 1/2 if second, 1/3 if third... 0 if absent
    mrr = sum(1 / r for r in ranks if r) / n
    return hits, mrr


by_type = {}   # question type -> list of ranks
archive_questions = 0
for q in questions:
    # safety net: if no chunk can ever match, the keywords are wrong
    if not any(is_correct(c, q) for c in chunks):
        print(f"BAD KEYWORDS  {q['question']}  (no chunk matches source + keywords)")
        continue

    # a question whose answer is in an archived document is asked "as if the student wanted the archive";
    # otherwise it could never be found (archived chunks are left out by default)
    in_archive = all(c.get("status") == "archive" for c in chunks if is_correct(c, q))
    archive_questions += in_archive
    top = retrieve(q["question"], TOP_K, include_archive=True if in_archive else None)
    rank = next((pos for pos, c in enumerate(top, start=1) if is_correct(c, q)), None)
    by_type.setdefault(q.get("type", "direct"), []).append(rank)

    if rank:
        print(f"OK    (rank {rank})  {q['question']}")
    else:
        print(f"MISS            {q['question']}")
        print(f"                top result was: {top[0]['source']} (page {top[0]['page']})")

all_ranks = [r for ranks in by_type.values() for r in ranks]

# ranks are measured in the top 8 for every question; this only shows which questions would get more chunks
enum = [q["question"] for q in questions if is_enumeration(q["question"])]
print(f"\n{len(enum)}/{len(questions)} questions detected as enumeration (they get {TOP_K_ENUM} chunks instead of {TOP_K})")
for text in enum:
    print("   ", text)
print(f"{archive_questions}/{len(questions)} questions have their answer in an archived document (searched with archives included)")

print(f"\n{'type':<14}{'n':>4}" + "".join(f"{'hit@' + str(k):>8}" for k in KS) + f"{'MRR':>8}")
for name, ranks in list(by_type.items()) + [("ALL", all_ranks)]:
    hits, mrr = metrics(ranks)
    print(f"{name:<14}{len(ranks):>4}" + "".join(f"{100 * hits[k]:>7.0f}%" for k in KS) + f"{mrr:>8.3f}")

if len(sys.argv) > 1:
    hits, mrr = metrics(all_ranks)
    if not RESULTS.exists():
        header = "| Date | Change | Questions | " + " | ".join(f"hit@{k}" for k in KS) + " | MRR |\n"
        RESULTS.write_text(header + "|---" * (4 + len(KS)) + "|\n", encoding="utf-8")
    row = (f"| {date.today()} | {' '.join(sys.argv[1:])} | {len(all_ranks)} | "
           + " | ".join(f"{100 * hits[k]:.0f}%" for k in KS) + f" | {mrr:.3f} |\n")
    with open(RESULTS, "a", encoding="utf-8") as f:
        f.write(row)
    print(f"\nLine added to {RESULTS}")
