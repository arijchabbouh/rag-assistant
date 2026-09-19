import sys
import pdfplumber

name, page_num = sys.argv[1], int(sys.argv[2])
with pdfplumber.open(f"documents/{name}") as pdf:
    text = pdf.pages[page_num - 1].extract_text() or ""
print("\n".join(text.splitlines()[:15]))