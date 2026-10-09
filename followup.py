import re
from itertools import zip_longest

from ask import generate
from build_prompt import retrieve, build_prompt, top_k_for

# beginnings that show the question continues the previous one ("et les DS ?", "pareil pour...")
FOLLOW_UP_STARTS = ("et ", "et,", "aussi", "pareil", "même chose", "meme chose", "mais ", "donc ")


def is_follow_up(question):
    """A follow-up is very short, or starts like one. If we are wrong, the merge below limits the damage."""
    q = question.strip().lower()
    words = re.findall(r"[^\W\d_]+", q)
    return q.startswith(FOLLOW_UP_STARTS) or len(words) <= 3


def merge(first, second, k):
    """Take chunks alternately from two rankings, without duplicates."""
    merged, seen = [], set()
    for a, b in zip_longest(first, second):
        for chunk in (a, b):
            if chunk is not None and chunk["id"] not in seen:
                seen.add(chunk["id"])
                merged.append(chunk)
    return merged[:k]


def ask_with_context(question, previous=None):
    """Like ask(), but a short follow-up is understood with the previous question of the student."""
    k = top_k_for(question)      # 8 normally, more for a "list them all" question
    if previous and is_follow_up(question):
        alone = retrieve(question, k)
        combined = retrieve(previous + " " + question, k)
        selected = merge(combined, alone, k)
        shown = (f"{question}\n(Cette question est peut-être la suite de la précédente : « {previous} ». "
                 f"Si c'est le cas, interprète-la dans ce contexte.)")
    else:
        selected = retrieve(question, k)
        shown = question

    answer = generate(build_prompt(shown, selected))
    cited = sorted({int(n) for n in re.findall(r"\[(\d+)\]", answer)})
    sources = [selected[n - 1] for n in cited if 1 <= n <= len(selected)]
    return answer, sources