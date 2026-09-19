import re
import pdfplumber
from pypdf import PdfReader

HOUR_LABELS = [("CI", "C.I"), ("TD", "TD"), ("PrTD", "Pr/TD"),
               ("Projet", "Projet"), ("TP", "TP")]

CALENDAR_TITLE = "Calendrier de l'année universitaire 26-27"


def clean(cell):
    return re.sub(r"\s+", " ", cell or "").strip()


# ---------------------------------------------------------------- study plans

def is_study_plan(path):
    return path.name.startswith("PE_") or path.name.startswith("Plans_d")


def normalize_header(cell):
    """Map the different header spellings to one standard name."""
    c = clean(cell).lower()
    if c == "c.i":
        return "CI"
    if c == "td":
        return "TD"
    if c in ("pr/td", "td/pr"):
        return "PrTD"
    if c in ("pr", "projet"):
        return "Projet"
    if c == "tp":
        return "TP"
    if c == "total":
        return "Total"
    if c == "coefficients":
        return "Coef"
    if c.startswith("coef") and "ue" in c:
        return "CoefUE"
    if c in ("cc", "contrôle continu", "contrôle"):
        return "CC"
    if c == "examen":
        return "Examen"
    return None


def study_plan_chunks(path):
    """Return a list of (page_number, text): one chunk per course + one summary per semester."""
    results = []
    semesters = {}
    ctx = {"formation": "", "annee": "", "option": "", "semestre": "",
           "validation": "", "ue_code": "", "ue_coef": "", "ue_name": ""}
    # course_col = position of the column that holds the course name (usually 1)
    state = {"col": {}, "generic": None, "course_col": 1}

    def set_ctx(key, value):
        if ctx[key] != value:
            ctx[key] = value
            ctx["ue_code"] = ctx["ue_coef"] = ctx["ue_name"] = ""   # new section: forget the UE

    def update_context(text):
        m = re.search(r"FORMATION D.INGENIEURS? EN ([^\n|]+)", text, re.I)
        if m:
            set_ctx("formation", clean(m.group(1)))
        m = re.search(r"Plan d.études? de la (\S+) année", text, re.I)
        if m:
            set_ctx("annee", m.group(1))
            set_ctx("option", "")          # options belong to one year
        m = re.search(r"Option\*?\s*:\s*([^\n|]+)", text, re.I)
        if m:
            set_ctx("option", clean(m.group(1)))
        m = re.search(r"Semestre\s*(\d+)", text, re.I)
        if m:
            set_ctx("semestre", f"Semestre {m.group(1)}")
        m = re.search(r"Validé CS \d+ \S+ \d{4}", text)
        if m:
            ctx["validation"] = m.group(0)

    def read_region(page, top, bottom):
        """Read the text of a horizontal band of the page (titles between tables)."""
        x0, y0, x1, y1 = page.bbox
        top, bottom = max(top, y0), min(bottom, y1)
        if bottom - top > 2:
            update_context(page.crop((x0, top, x1, bottom)).extract_text() or "")

    def head():
        parts = ["Plan d'études",
                 f"Formation d'ingénieurs en {ctx['formation'] or path.stem}"]
        if ctx["annee"]:
            parts.append(f"{ctx['annee']} année")
        if ctx["option"]:
            parts.append(f"Option : {ctx['option']}")
        if ctx["semestre"]:
            parts.append(ctx["semestre"])
        text = " — ".join(parts)
        if ctx["validation"]:
            text += f" ({ctx['validation']})"
        return text

    def get(row, name):
        i = state["col"].get(name)
        return row[i] if i is not None and i < len(row) else ""

    with pdfplumber.open(path) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            tables = sorted(page.find_tables(), key=lambda t: t.bbox[1])
            prev = page.bbox[1]

            for t in tables:
                read_region(page, prev, t.bbox[1])   # titles above this table

                for raw in t.extract():
                    row = [clean(c) for c in raw]
                    filled = [c for c in row if c]
                    if not filled:
                        continue

                    # title-like rows (few filled cells) can carry the context
                    if len(filled) <= 3:
                        update_context(" ".join(filled))

                    # where is the course-name column? It moves when a table
                    # has an extra column for the UE name.
                    # Only look in HEADER rows (first cell is exactly "UE"),
                    # because some UE names also start with "Eléments".
                    if row[0] == "UE":
                        for i, c in enumerate(row):
                            if c.lower().startswith(("eléments", "éléments")):
                                state["course_col"] = i

                    # header row with C.I: remember which column is which
                    norm = [normalize_header(c) for c in row]
                    if "CI" in norm:
                        state["col"] = {n: i for i, n in enumerate(norm) if n}
                        state["generic"] = None
                        continue

                    # header row of a different kind of table (e.g. semester 6)
                    if row[0] == "UE":
                        state["col"] = {}
                        state["generic"] = row
                        continue

                    # tables without C.I columns: "header : value" pairs
                    if not state["col"]:
                        if state["generic"] and len(filled) >= 3 and "total" not in row[0].lower():
                            pairs = [f"{h} : {v}" for h, v in zip(state["generic"], row) if h and v]
                            results.append((page_num, f"{head()} — " + " ; ".join(pairs) + "."))
                        continue

                    # UE code: only the first course of a UE has it, so carry it forward
                    cc = state["course_col"]
                    if row[0].startswith("UE") and row[0] != "UE":
                        ctx["ue_code"] = row[0]
                        ctx["ue_coef"] = get(row, "CoefUE")
                        ctx["ue_name"] = row[1] if cc > 1 and len(row) > 1 else ""

                    course = row[cc] if len(row) > cc else ""
                    if not course or "(ee)" in course.lower():
                        continue
                    if course.lower() in ("unité", "unite") or "total" in row[0].lower():
                        continue
                    keys = ("Total", "CI", "TD", "PrTD", "Projet", "TP")
                    if not any(get(row, k) for k in keys):
                        continue

                    hours = [f"{label} {get(row, key)} h"
                             for key, label in HOUR_LABELS if get(row, key)]
                    evals = []
                    cc_cell = get(row, "CC")
                    if cc_cell:
                        extra = [w for w in ("oral", "projet") if w in cc_cell.lower()]
                        evals.append("contrôle continu" + (f" ({', '.join(extra)})" if extra else ""))
                    if get(row, "Examen"):
                        evals.append("examen")

                    ue_part = ""
                    if ctx["ue_code"]:
                        details = []
                        if ctx["ue_name"]:
                            details.append(ctx["ue_name"])
                        if ctx["ue_coef"]:
                            details.append(f"coefficient UE : {ctx['ue_coef']}")
                        ue_part = ctx["ue_code"]
                        if details:
                            ue_part += f" ({', '.join(details)})"
                        ue_part += " — "

                    total = get(row, "Total")
                    text = (
                        f"{head()} — {ue_part}Matière : {course}. "
                        f"Volume horaire : {', '.join(hours)}"
                        + (f" ; total {total} h" if total else "") + ". "
                        f"Crédits/coefficient : {get(row, 'Coef')}. "
                        f"Évaluation : {', '.join(evals) if evals else 'non précisée'}."
                    )
                    results.append((page_num, text))

                    key = (ctx["formation"], ctx["annee"], ctx["option"], ctx["semestre"])
                    entry = semesters.setdefault(key, {"page": page_num, "courses": []})
                    entry["courses"].append(course)

                prev = t.bbox[3]

            read_region(page, prev, page.bbox[3])   # text below the last table

    for (formation, annee, option, semestre), entry in semesters.items():
        parts = ["Liste des matières",
                 f"Formation d'ingénieurs en {formation or path.stem}"]
        if annee:
            parts.append(f"{annee} année")
        if option:
            parts.append(f"Option : {option}")
        if semestre:
            parts.append(semestre)
        results.append((entry["page"],
                        " — ".join(parts) + " : " + "; ".join(entry["courses"]) + "."))
    return results


# ------------------------------------------------------------------- calendar

DAYS = r"(?:LUN|MAR|MER|JEU|VEN|SAM|DIM)"
MONTHS = r"(?:sept|oct|nov|d[ée]c|janv|f[ée]vr|mars|avr|mai|juin|juil|ao[uû]t)"
# a day name followed by day-of-month numbers (noise), stopping before the real date
DAY_PREFIX = re.compile(rf"^{DAYS}\s+(?:\d+\*?\s+(?!{MONTHS}\b))*", re.I)
DATE_START = re.compile(rf"^\d{{1,2}}(?:\s*-\s*\d{{1,2}})?\s*-?\s*{MONTHS}\b", re.I)


def is_calendar(path):
    return path.name.startswith("Calendrier")


def calendar_chunks(path):
    """One chunk per calendar line: 'date + event', without the grid of day numbers."""
    results = []
    for page_num, page in enumerate(PdfReader(path).pages, start=1):
        for line in (page.extract_text() or "").splitlines():
            rest = DAY_PREFIX.sub("", clean(line), count=1)
            if not DATE_START.match(rest):
                continue
            after_date = DATE_START.sub("", rest, count=1)
            if not re.search(r"[A-Za-zÀ-ÿ]{4,}", after_date):
                continue
            results.append((page_num, f"{CALENDAR_TITLE} — {rest}"))
    return results