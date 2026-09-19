import json
from pathlib import Path

QUESTIONS = Path("eval_questions.json")
chunks = json.load(open("chunks.json", encoding="utf-8"))

questions = []
if QUESTIONS.exists():
    try:
        questions = json.load(open(QUESTIONS, encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"eval_questions.json has a syntax error ({e}).")
        print("Rename it (for example to eval_questions_old.json) and run this script again.")
        raise SystemExit

print(f"{len(questions)} questions so far. Leave the question empty to stop.\n")

while True:
    question = input("Question (in your own words): ").strip()
    if not question:
        break
    source = input("Part of the file name (e.g. PE_Mecatronique, Guide, Calendrier): ").strip()
    raw = input("Text that must appear in the right chunk (separate several with ;): ")
    keywords = [k.strip() for k in raw.split(";") if k.strip()]

    matches = [c for c in chunks
               if source.lower() in c["source"].lower()
               and all(k.lower() in c["text"].lower() for k in keywords)]
    if not matches:
        print('  -> No chunk matches. Check the spelling with: python find_chunk.py "a word"\n')
        continue

    print(f"  -> {len(matches)} chunk(s) match. First one:")
    print(f"     {matches[0]['source']} (page {matches[0]['page']}): {matches[0]['text'][:300]}")
    if len(matches) > 3:
        print("  (many chunks match: your keywords may be too general)")
    if input("  Save this question? (y/n): ").strip().lower() == "y":
        questions.append({"question": question, "source": source, "keywords": keywords})
        QUESTIONS.write_text(json.dumps(questions, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  saved ({len(questions)} questions in total)\n")

print("Done.")