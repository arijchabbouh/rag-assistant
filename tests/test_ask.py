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

    def generate_content(self, model, contents, config=None):
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


# ------------------------------------------------------------------ retry after a refusal

def scripted_generate(monkeypatch, replies):
    """ask.generate returns the replies in order (an Exception is raised); records every prompt."""
    prompts, replies = [], list(replies)

    def fake(prompt, temperature=None):
        prompts.append(prompt)
        reply = replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply

    monkeypatch.setattr(ask, "generate", fake)
    return prompts


def fake_retrieve(monkeypatch):
    searched = []

    def fake(question, k=None, **kwargs):
        searched.append(question)
        return [{"id": len(searched), "source": f"doc{len(searched)}.pdf", "page": 1, "text": question}]

    monkeypatch.setattr(ask, "retrieve", fake)
    return searched


def test_answered_question_costs_one_call(monkeypatch):
    prompts = scripted_generate(monkeypatch, ["Le forum a lieu le 17 novembre [1]."])
    fake_retrieve(monkeypatch)
    answer, sources = ask.ask("forum entreprises date")
    assert answer == "Le forum a lieu le 17 novembre [1]."
    assert len(prompts) == 1 and len(sources) == 1


def test_refusal_is_rephrased_searched_again_and_answered(monkeypatch):
    prompts = scripted_generate(monkeypatch, [
        ask.REFUSAL,
        "Le rapport de PFE peut-il être confidentiel ?",          # the rephrased question
        "Non, il doit être archivé [1].",
    ])
    searched = fake_retrieve(monkeypatch)
    answer, sources = ask.ask("Le rapport de PFE  confidentiel ?")
    assert answer == "Non, il doit être archivé [1]."
    assert searched == ["Le rapport de PFE  confidentiel ?", "Le rapport de PFE peut-il être confidentiel ?"]
    assert sources[0]["source"] == "doc2.pdf"                       # cited from the second search
    assert "Le rapport de PFE  confidentiel ?" in prompts[1]         # the rephrasing prompt
    assert "Question posée par l'étudiant" in prompts[2]
    assert len(prompts) == 3


def test_second_refusal_is_kept_with_a_hint(monkeypatch):
    prompts = scripted_generate(monkeypatch, [ask.REFUSAL, "Quel est le menu de la cantine ?", ask.REFUSAL])
    fake_retrieve(monkeypatch)
    answer, sources = ask.ask("menu cantine")
    assert answer == f"{ask.REFUSAL}\n\n{ask.REPHRASE_HINT}"
    assert sources == [] and len(prompts) == 3


def test_same_question_after_rephrasing_is_not_retried(monkeypatch):
    prompts = scripted_generate(monkeypatch, [ask.REFUSAL, "Quel est le menu de la cantine ?"])
    fake_retrieve(monkeypatch)
    answer, _ = ask.ask("quel est le menu de la cantine ?")
    assert answer.endswith(ask.REPHRASE_HINT) and len(prompts) == 2


def test_gemini_down_during_retry_keeps_the_first_refusal(monkeypatch):
    scripted_generate(monkeypatch, [ask.REFUSAL, ask.GeminiUnavailable(ask.BUSY_MESSAGE)])
    fake_retrieve(monkeypatch)
    answer, _ = ask.ask("PFE durée minimum")
    assert answer == f"{ask.REFUSAL}\n\n{ask.REPHRASE_HINT}"


@pytest.mark.parametrize("answer, refused", [
    (ask.REFUSAL, True),
    (f"« {ask.REFUSAL} »", True),
    (f"{ask.REFUSAL} Les extraits précisent seulement que...", True),
    ("Le forum a lieu le 17 novembre [1].", False),
    ("Selon le guide, je ne trouve pas cette information pour les M2, mais...", False),
])
def test_is_refusal(answer, refused):
    assert ask.is_refusal(answer) is refused
