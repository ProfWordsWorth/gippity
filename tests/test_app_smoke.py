from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import os

from lectio_plus.app import FakeLLM, OpenAILLM, create_app, run


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


def test_ollama_provider_offline(monkeypatch) -> None:
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


def test_create_app_get_returns_ok() -> None:
    app = create_app()
    client = app.test_client()
    resp = client.get("/")
    assert resp.status_code == 200


def test_post_run_injects_metadata(monkeypatch) -> None:
    outputs = [
        "reflection",
        '{"title": "T", "artist": "A", "year": "2000", "image_url": "https://upload.wikimedia.org/x.jpg"}',
        "<h1>Current Date</h1><p>Cover Title by Cover Artist (Cover Year)</p><img src='cid:cover.jpg'>",
    ]

    def fake_generate(self, model, prompt, temperature=0.2, max_tokens=None):
        return outputs.pop(0)

    monkeypatch.setattr(FakeLLM, "generate", fake_generate)
    app = create_app()
    client = app.test_client()
    resp = client.post("/run", data={"date": "2024-05-04"})
    html = resp.get_data(as_text=True)
    assert resp.headers["Content-Type"] == "text/html; charset=utf-8"
    assert "Current Date" not in html
    assert "Cover Title" not in html
    assert "Cover Artist" not in html
    assert "Cover Year" not in html
    assert "cid:cover.jpg" not in html
    assert "2024-05-04" in html
    assert "T" in html and "A" in html and "2000" in html
    assert "https://upload.wikimedia.org/x.jpg" in html


def test_healthz_ok_with_ollama_monkeypatched(monkeypatch) -> None:
    def fake_generate(self, model, prompt, temperature=0.2, max_tokens=None):  # noqa: ARG001
        return "pong"

    monkeypatch.setattr(OpenAILLM, "generate", fake_generate)
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    monkeypatch.setenv("OPENAI_BASE_URL", "http://localhost:11434/v1")
    monkeypatch.setenv("OPENAI_API_KEY", "ollama")

    app = create_app()
    client = app.test_client()
    resp = client.get("/healthz")
    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data, dict)
    assert data.get("ok") is True
