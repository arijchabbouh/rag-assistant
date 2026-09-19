from pathlib import Path
from pypdf import PdfReader
from docx import Document

files = sorted(
    p for p in Path("documents").iterdir()
    if p.is_file() and p.suffix.lower() in {".pdf", ".docx"}
)
print(f"{len(files)} files found\n")

total_chars = 0
for f in files:
    if f.suffix.lower() == ".pdf":
        reader = PdfReader(f)
        text = "".join((page.extract_text() or "") for page in reader.pages)
        size = f"{len(reader.pages)} pages"
    else:
        doc = Document(f)
        parts = [p.text for p in doc.paragraphs]
        for table in doc.tables:
            for row in table.rows:
                parts.append(" | ".join(cell.text for cell in row.cells))
        text = "\n".join(parts)
        size = "Word file"
    total_chars += len(text)
    print(f"{f.name}: {size}, {len(text)} characters")

print(f"\nTotal: {total_chars} characters")