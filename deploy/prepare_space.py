"""Builds space_build/: exactly the files the Hugging Face Space needs, nothing else (allow-list).

    python deploy/prepare_space.py
    hf upload <your-name>/<space-name> space_build . --repo-type space

An allow-list rather than "upload the project minus some folders": a file that is not listed here
(school documents, .env, feedback.jsonl, a new personal file...) can never reach the Space by mistake.
See DEPLOY.md.
"""
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "space_build"

FILES = [
    # container
    "Dockerfile", ".dockerignore", "requirements-deploy.txt",
    # code that runs in the Space
    "api.py", "ask.py", "build_prompt.py", "followup.py", "config.py",
    # data: titles/status, typo-fixer word list, and the index built from the documents (not the documents)
    "documents_status.json", "french_words.txt", "chunks.json", "embeddings.npy",
    # web page sources (built inside the container)
    "frontend/package.json", "frontend/package-lock.json", "frontend/index.html", "frontend/vite.config.js",
    "public/LOGO.jpg",
]
FOLDERS = ["frontend/src"]
NEVER = ("documents/", ".env", "feedback.jsonl", "listes-etudiants/", "mise_de_cote/", "a_ocr/", "plus_tard/")


def fail(message):
    print(f"ERROR: {message}")
    raise SystemExit(1)


def check_index():
    """chunks.json and embeddings.npy must exist and match (same number of chunks)."""
    for name in ("chunks.json", "embeddings.npy"):
        if not (ROOT / name).exists():
            fail(f"{name} is missing: run python chunk_documents.py then python embed_chunks.py first.")
    chunks = json.loads((ROOT / "chunks.json").read_text(encoding="utf-8"))
    import numpy as np
    rows = np.load(ROOT / "embeddings.npy", mmap_mode="r").shape[0]
    if rows != len(chunks):
        fail(f"chunks.json has {len(chunks)} chunks but embeddings.npy has {rows} rows: "
             "run python embed_chunks.py again.")
    missing = sorted({c.get("status") is None and c["source"] for c in chunks} - {False})
    if missing:
        fail(f"chunks without a status (old chunks.json?): {missing[:3]}... run python chunk_documents.py")
    return len(chunks)


def main():
    n_chunks = check_index()
    if OUT.exists():
        shutil.rmtree(OUT)
    copied = []
    for name in FILES:
        src = ROOT / name
        if not src.exists():
            fail(f"{name} is missing")
        dst = OUT / name
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        copied.append(name)
    for folder in FOLDERS:
        for src in sorted((ROOT / folder).rglob("*")):
            if src.is_file():
                rel = src.relative_to(ROOT).as_posix()
                dst = OUT / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
                copied.append(rel)
    # the Space reads its settings (Docker, port 7860) from the front matter of its README.md
    shutil.copy2(ROOT / "deploy" / "space_README.md", OUT / "README.md")
    copied.append("README.md")

    bad = [c for c in copied if c.startswith(NEVER)]
    if bad:
        fail(f"refusing to prepare: {bad}")
    total = sum((OUT / c).stat().st_size for c in copied)
    print(f"space_build/ ready: {len(copied)} files, {total / 1e6:.1f} MB, index of {n_chunks} chunks.")
    for c in copied:
        print("  ", c)
    print("\nNext (see DEPLOY.md): hf upload <your-name>/<space-name> space_build . --repo-type space")


if __name__ == "__main__":
    sys.exit(main())
