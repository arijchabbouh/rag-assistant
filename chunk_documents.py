import json
import re
from pathlib import Path
from pypdf import PdfReader
from docx import Document
from table_chunks import is_study_plan, study_plan_chunks, is_calendar, calendar_chunks
from article_chunks import is_guide, guide_chunks

CHUNK_SIZE = 800   # max characters per chunk
OVERLAP = 150      # characters shared between two consecutive chunks


def read_pages(path):
    """Return a list of (page_number, text) for a PDF or Word file."""
    if path.suffix.lower() == ".pdf":
        reader = PdfReader(path)
        return [(i + 1, page.extract_text() or "") for i, page in enumerate(reader.pages)]
    doc = Document(path)
    parts = [p.text for p in doc.paragraphs]
    for table in doc.tables:
        for row in table.rows:
            parts.append(" | ".join(cell.text for cell in row.cells))
    return [(1, "\n".join(parts))]


def split_text(text, size=CHUNK_SIZE, overlap=OVERLAP):
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        if end < len(text):
            # try to cut at a paragraph, line break or sentence end
            cut = max(text.rfind("\n\n", start, end),
                      text.rfind("\n", start, end),
                      text.rfind(". ", start, end))
            if cut > start + size // 2:
                end = cut + 1
        piece = text[start:end].strip()
        if piece:
            chunks.append(piece)
        if end >= len(text):
            break
        start = max(end - overlap, start + 1)
    return chunks


files = sorted(
    p for p in Path("documents").iterdir()
    if p.is_file() and p.suffix.lower() in {".pdf", ".docx"}
)

all_chunks = []
for f in files:
    pieces = []  # list of (page, text)
    mode = "texte"
    is_pdf = f.suffix.lower() == ".pdf"
    if is_pdf and is_study_plan(f):
        pieces = study_plan_chunks(f)
        mode = "tableaux"
    elif is_pdf and is_calendar(f):
        pieces = calendar_chunks(f)
        mode = "calendrier"
    elif is_pdf and is_guide(f):
        pieces = guide_chunks(f)
        mode = "articles"
    if not pieces:
        mode = "texte"
        for page_num, text in read_pages(f):
            for piece in split_text(text):
                pieces.append((page_num, piece))

    count = 0
    for page_num, piece in pieces:
        if len(piece) < 30:
            continue
        all_chunks.append({
            "id": len(all_chunks),
            "source": f.name,
            "page": page_num,
            "text": piece,
        })
        count += 1
    print(f"{f.name}: {count} chunks ({mode})")

Path("chunks.json").write_text(
    json.dumps(all_chunks, ensure_ascii=False, indent=2), encoding="utf-8"
)
print(f"\nTotal: {len(all_chunks)} chunks saved to chunks.json")