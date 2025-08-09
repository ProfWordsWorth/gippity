from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import os

from lectio_plus.app import FakeLLM, OpenAILLM, run


def test_app_run_returns_html() -> None:
    html = run("Hi")
    assert html.startswith("<html>")
    assert html.endswith("</html>")


def test_default_provider_uses_fake_llm(monkeypatch) -> None:
    outputs = [
        "reflection",
        '{"title": "T", "artist": "A", "year": "2000", "image_url": "https://upload.wikimedia.org/x.jpg"}',
        "<p>done</p>",
    ]

    def fake_generate(self, model, prompt, temperature=0.2, max_tokens=None):
        return outputs.pop(0)

    monkeypatch.setattr(FakeLLM, "generate", fake_generate)
    os.environ.pop("LLM_PROVIDER", None)
    html = run("block")
    assert "<p>done</p>" in html
    assert "<<" not in html and ">>" not in html


def test_ollama_provider(monkeypatch) -> None:
    outputs = [
        "reflection",
        '{"title": "T", "artist": "A", "year": "2000", "image_url": "https://upload.wikimedia.org/x.jpg"}',
        "<p>done</p>",
    ]

    def fake_generate(self, model, prompt, temperature=0.2, max_tokens=None):
        return outputs.pop(0)

    monkeypatch.setattr(OpenAILLM, "generate", fake_generate)
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    monkeypatch.setenv("OPENAI_BASE_URL", "http://localhost:11434/v1")
    monkeypatch.setenv("OPENAI_API_KEY", "ollama")

    html = run("block")
    assert "<p>done</p>" in html
