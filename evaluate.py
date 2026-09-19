import json
from build_prompt import retrieve, chunks, TOP_K

questions = json.load(open("eval_questions.json", encoding="utf-8"))


def is_correct(chunk, q):
    """Correct = right file AND all the keywords appear in the chunk."""
    if q["source"].lower() not in chunk["source"].lower():
        return False
    text = chunk["text"].lower()
    return all(k.lower() in text for k in q["keywords"])


valid = in5 = inK = first = 0
for q in questions:
    # safety net: if no chunk can ever match, the keywords are wrong
    if not any(is_correct(c, q) for c in chunks):
        print(f"BAD KEYWORDS  {q['question']}  (no chunk matches source + keywords)")
        continue
    valid += 1

    top = retrieve(q["question"], TOP_K)
    rank = next((pos for pos, c in enumerate(top, start=1) if is_correct(c, q)), None)

    if rank:
        inK += 1
        in5 += rank <= 5
        first += rank == 1
        print(f"OK    (rank {rank})  {q['question']}")
    else:
        print(f"MISS            {q['question']}")
        print(f"                top result was: {top[0]['source']} (page {top[0]['page']})")

print(f"\nRecall@5:  {in5}/{valid} = {100 * in5 / valid:.0f}%")
print(f"Recall@{TOP_K}: {inK}/{valid} = {100 * inK / valid:.0f}%   (what the assistant actually receives)")
print(f"Right chunk ranked first: {first}/{valid} = {100 * first / valid:.0f}%")