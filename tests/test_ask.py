"""ask.generate(): model fallback, with a fake Gemini client (no network)."""
import os
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest

ROOT = Path(__file__).resolve().parent.parent
os.chdir(ROOT)
os.environ.setdefault("GEMINI_API_KEY", "test-key")

if not (ROOT / "chunks.json").exists() or not (ROOT / "embeddings.npy").exists():
    pytest.skip("chunks.json / embeddings.npy missing", allow_module_level=True)

import ask  # noqa: E402


class FakeModels:
    """Each model name maps to an exception to raise, or to the text to return."""

    def __init__(self, behaviour):
        self.behaviour = behaviour
        self.calls = []

    def generate_content(self, model, contents):
        self.calls.append(model)
        result = self.behaviour[model]
        if isinstance(result, Exception):
            raise result
        return SimpleNamespace(text=result)


def fake_client(monkeypatch, behaviour):
    models = FakeModels(behaviour)
    monkeypatch.setattr(ask, "client", SimpleNamespace(models=models))
    monkeypatch.setattr(ask, "MODELS", list(behaviour))
    monkeypatch.setattr(ask.time, "sleep", lambda s: None)
    return models


def test_client_has_a_timeout():
    assert ask.client._api_client._http_options.timeout == ask.TIMEOUT_MS == 30_000


@pytest.mark.parametrize("error", [
    httpx.ReadTimeout("The read operation timed out"),
    httpx.ConnectTimeout("timed out"),
])
def test_timeout_falls_back_to_next_model(monkeypatch, error):
    models = fake_client(monkeypatch, {"slow": error, "fast": "Réponse [1]"})
    assert ask.generate("prompt") == "Réponse [1]"
    assert models.calls == ["slow", "fast"]


def test_all_models_time_out_gives_busy_message(monkeypatch):
    fake_client(monkeypatch, {"a": httpx.ReadTimeout("timed out"), "b": httpx.ConnectTimeout("timed out")})
    with pytest.raises(ask.GeminiUnavailable) as info:
        ask.generate("prompt")
    assert info.value.user_message == ask.BUSY_MESSAGE


def test_unknown_error_is_not_swallowed(monkeypatch):
    fake_client(monkeypatch, {"a": ValueError("bug"), "b": "never reached"})
    with pytest.raises(ValueError):
        ask.generate("prompt")
