import json
import re

MONTHS = r"(?:sept|oct|nov|d[ée]c|janv|f[ée]vr|mars|avr|mai|juin|juil|ao[uû]t)"
# a calendar date at the start of a line: "17-nov", "1-3 sept", "21 sept-30 sept", "30 nov- 12 dec"
DATE = re.compile(rf"^\d{{1,2}}(?:\s*-\s*\d{{1,2}})?\s*-?\s*{MONTHS}\b(?:\s*-\s*\d{{1,2}}\s*{MONTHS}\b)?", re.I)


def build_suggestions(chunks_path="chunks.json", eval_path="eval_questions.json", limit=700):
    """Questions proposed while the student types, built from the documents themselves."""
    suggestions = []

    # 1. the questions you wrote and tested yourself
    try:
        suggestions += [q["question"] for q in json.load(open(eval_path, encoding="utf-8"))]
    except FileNotFoundError:
        pass

    chunks = json.load(open(chunks_path, encoding="utf-8"))
    guide, calendar, courses = [], [], []
    for c in chunks:
        text = c["text"]

        m = re.search(r"Art\.?\s*\d+\s+(.+?)\s*:", text)                    # Guide articles
        if m and text.startswith("Guide"):
            guide.append(f"Que dit le guide de l'élève sur « {m.group(1)} » ?")

        if text.startswith("Calendrier") and " — " in text:                 # calendar lines
            line = text.split(" — ", 1)[1]
            d = DATE.match(line)
            if d and line[d.end():].strip():
                calendar.append(f"Quand a lieu : {line[d.end():].strip()} ?")

        m = re.search(r"Matière : (.+?)\. Volume horaire", text)            # courses in study plans
        if m:
            courses.append(f"Combien d'heures et quel coefficient pour le cours {m.group(1).strip()} ?")

    seen, result = set(), []
    for s in suggestions + guide + calendar + courses:
        if s.lower() not in seen:
            seen.add(s.lower())
            result.append(s)
    return result[:limit]


if __name__ == "__main__":
    items = build_suggestions()
    print(len(items), "suggestions. Examples:")
    for s in items[:: max(1, len(items) // 12)]:
        print("  -", s)