"""Query synonyms (build_prompt.SYNONYMS): students' words -> the documents' wording. Real retrieval."""
import os
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
os.chdir(ROOT)

if not (ROOT / "chunks.json").exists() or not (ROOT / "embeddings.npy").exists():
    pytest.skip("chunks.json / embeddings.npy missing", allow_module_level=True)

from build_prompt import expand, retrieve  # noqa: E402


def test_options_adds_the_study_plan_wording():
    assert "panier d'option" in expand("quelles sont les options en 3ème année informatique ?")


def test_options_question_finds_the_baskets():
    selected = retrieve("quelles sont les options en 3ème année informatique ?")
    baskets = [c for c in selected if c["source"].startswith("PE_Informatique") and "Panier" in c["text"]]
    # before the synonyms: 4 of 25, the first at rank 9, and no chunk explaining what a "panier" is
    assert len(baskets) >= 10
    # the footnote "choisir 6 matières optionnelles ... chaque panier d'option" is near the top
    assert any(c["source"].startswith("PE_Informatique") and "matières optionnelles" in c["text"]
               for c in selected[:3])
    assert {"Panier SI", "Panier Rx", "Panier Emb"} <= {p for c in baskets for p in ("Panier SI", "Panier Rx", "Panier Emb") if p in c["text"]}


def test_question_about_the_past_keeps_the_old_wording():
    question = "quelles étaient les anciennes options avant 2026"
    assert "panier" not in expand(question)
    selected = retrieve(question)
    assert any(c["source"].startswith("Plaquette_Dep_Informatique_2017") for c in selected)


def test_words_containing_option_are_not_matched():
    assert "panier" not in expand("les matières optionnelles")   # already the documents' word


def test_prompt_tells_the_model_the_documents_wording():
    from build_prompt import build_prompt
    question = "quelles sont les options en 3ème année informatique ?"
    assert "Vocabulaire des documents pour cette question : panier d'option" in build_prompt(question, [])
    assert "Vocabulaire des documents" not in build_prompt("quand est le forum des entreprises ?", [])
