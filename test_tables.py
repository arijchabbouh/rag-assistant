import sys
import pdfplumber

name, page_num = sys.argv[1], int(sys.argv[2])
with pdfplumber.open(f"documents/{name}") as pdf:
    page = pdf.pages[page_num - 1]
    tables = page.extract_tables()
    print(f"{len(tables)} table(s) found\n")
    for t in tables:
        for row in t[:30]:
            print(row)
        print()