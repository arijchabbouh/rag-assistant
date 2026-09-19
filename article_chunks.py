import re
from pypdf import PdfReader

GUIDE_TITLE = "Guide de l'élève ingénieur ENICarthage 2024-2025"
MAX_CHARS = 1200

# an article starts at the beginning of a line with "Art. 17" (or "Art 17")
ARTICLE_START = re.compile(r"(?m)^[ \t]*(?=Art\.?\s*\d+\b)")


def is_guide(path):
    return path.name.startswith("Guide_")


def split_long(text, header):
    """Cut a long article at line breaks; every continuation repeats the article title."""
    if len(text) <= MAX_CHARS:
        return [text]
    pieces, current = [], ""
    for line in text.split("\n"):
        if current and len(current) + len(line) + 1 > MAX_CHARS:
            pieces.append(current.strip())
            current = f"{header} (suite)\n"
        current += line + "\n"
    if current.strip():
        pieces.append(current.strip())
    return pieces


def guide_chunks(path):
    """One chunk per article. Returns [] if no 'Art. N' marker is found."""
    full, page_starts = "", []
    for page_num, page in enumerate(PdfReader(path).pages, start=1):
        page_starts.append((len(full), page_num))
        full += (page.extract_text() or "") + "\n"

    def page_at(offset):
        page = 1
        for start, num in page_starts:
            if start <= offset:
                page = num
        return page

    cuts = [m.start() for m in ARTICLE_START.finditer(full)]
    if not cuts:
        return []

    results = []
    for a, b in zip(cuts, cuts[1:] + [len(full)]):
        text = re.sub(r"[ \t]+", " ", full[a:b])
        text = re.sub(r"\n\s*\n+", "\n", text).strip()
        header = text.split("\n")[0][:90]
        for piece in split_long(text, header):
            results.append((page_at(a), f"{GUIDE_TITLE} — {piece}"))
    return results