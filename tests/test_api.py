"""API tests. Retrieval is real (needs chunks.json + embeddings.npy); Gemini is replaced by a fake.

Run: python -m pytest -q
"""
import json
import os
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
os.chdir(ROOT)                                      # the pipeline opens chunks.json with a relative path
os.environ.setdefault("GEMINI_API_KEY", "test-key")  # never used: generate() is faked below

if not (ROOT / "chunks.json").exists() or not (ROOT / "embeddings.npy").exists():
    pytest.skip("chunks.json / embeddings.npy missing: run chunk_documents.py and embed_chunks.py",
                allow_module_level=True)

from fastapi.testclient import TestClient  # noqa: E402

import api  # noqa: E402


@pytest.fixture(scope="module")
def client():
    with TestClient(api.app) as c:     # runs the lifespan: the model is loaded once for all tests
        yield c


@pytest.fixture(autouse=True)
def fresh_limits():
    api.limiter.reset()


@pytest.fixture
def fake_gemini(client, monkeypatch):
    """Replace the Gemini call; returns the list of prompts it received."""
    prompts = []

    def fake_generate(prompt):
        prompts.append(prompt)
        return "Le forum des entreprises a lieu à la date indiquée [1]. Voir aussi [99]."

    monkeypatch.setattr(api.pipeline["followup"], "generate", fake_generate)
    return prompts


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["model_loaded"] is True
    assert body["chunks"] == len(json.load(open("chunks.json", encoding="utf-8")))


def test_ask(client, fake_gemini):
    r = client.post("/ask", json={"question": "quand est le forum des entreprises ?", "previous": None})
    assert r.status_code == 200
    body = r.json()
    assert body["answer"].startswith("Le forum")
    assert len(fake_gemini) == 1 and "forum" in fake_gemini[0].lower()
    # [1] is a valid citation, [99] is out of range and dropped
    assert [s["n"] for s in body["sources"]] == [1]
    source = body["sources"][0]
    assert set(source) == {"n", "source", "page", "text"}
    assert source["text"] in fake_gemini[0]     # the cited chunk is the first excerpt of the prompt
    assert "corrected_query" in body


def test_ask_corrected_query(client, fake_gemini):
    r = client.post("/ask", json={"question": "QUAND EST LE FORUM DES ENTREPRISES"})
    assert r.status_code == 200
    assert r.json()["corrected_query"] == "quand est le forum des entreprises"


@pytest.mark.parametrize("question", ["", "   ", "x" * 501])
def test_ask_invalid_question(client, fake_gemini, question):
    r = client.post("/ask", json={"question": question})
    assert r.status_code == 422
    assert fake_gemini == []


def test_ask_gemini_unavailable(client, monkeypatch):
    ask = api.pipeline["ask"]

    def down(prompt):
        raise ask.GeminiUnavailable(ask.BUSY_MESSAGE)

    monkeypatch.setattr(api.pipeline["followup"], "generate", down)
    r = client.post("/ask", json={"question": "quand est le forum des entreprises ?"})
    assert r.status_code == 503
    assert r.json()["detail"] == ask.BUSY_MESSAGE


def test_ask_unexpected_error_is_hidden(client, monkeypatch, caplog):
    def broken(prompt):
        raise ValueError("secret internal detail")

    monkeypatch.setattr(api.pipeline["followup"], "generate", broken)
    r = client.post("/ask", json={"question": "quand est le forum des entreprises ?"})
    assert r.status_code == 500
    assert r.json()["detail"] == api.INTERNAL_ERROR
    assert "secret internal detail" not in r.text
    assert "secret internal detail" in caplog.text     # ...but it is in the logs


def test_feedback_appends_a_line(client, tmp_path, monkeypatch):
    path = tmp_path / "feedback.jsonl"
    monkeypatch.setattr(api, "FEEDBACK_FILE", path)
    for comment in ("La date est fausse", None):
        r = client.post("/feedback", json={"question": "quand est le forum ?", "answer": "Le 3 mars [1].",
                                           "comment": comment})
        assert r.status_code == 201
    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    first = json.loads(lines[0])
    assert first["question"] == "quand est le forum ?"
    assert first["answer"] == "Le 3 mars [1]."
    assert first["comment"] == "La date est fausse"
    assert first["timestamp"].endswith("+00:00")
    assert json.loads(lines[1])["comment"] is None


def test_rate_limit(client, fake_gemini):
    codes = [client.post("/ask", json={"question": "forum"}).status_code for _ in range(api.RATE_LIMIT + 1)]
    assert codes[:-1] == [200] * api.RATE_LIMIT
    assert codes[-1] == 429


def test_cors_allows_react_dev_server(client):
    r = client.options("/ask", headers={"Origin": "http://localhost:5173",
                                        "Access-Control-Request-Method": "POST"})
    assert r.headers.get("access-control-allow-origin") == "http://localhost:5173"
    r = client.options("/ask", headers={"Origin": "http://evil.example",
                                        "Access-Control-Request-Method": "POST"})
    assert "access-control-allow-origin" not in r.headers
