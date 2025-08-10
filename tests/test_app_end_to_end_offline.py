from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lectio_plus.app import create_app, OpenAILLM
from lectio_plus import scrape


def test_run_offline_uses_fixture(monkeypatch) -> None:
    html = Path("fixtures/usccb/sample_1.html").read_text(encoding="utf-8")

    def fake_fetch(date_str: str):  # noqa: ARG001
        return html, "https://bible.usccb.org/bible/readings/20250809.cfm"

    monkeypatch.setattr(scrape, "fetch_usccb", fake_fetch)

    outputs = [
        "reflection",
        '{"title": "T", "artist": "A", "year": "2000", "image_url": "https://upload.wikimedia.org/x.jpg"}',
    ]

    def fake_generate(self, model, prompt, temperature=0.2, max_tokens=None):  # noqa: ARG001
        return outputs.pop(0)

    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    monkeypatch.setenv("OPENAI_BASE_URL", "http://localhost:11434/v1")
    monkeypatch.setenv("OPENAI_API_KEY", "ollama")
    monkeypatch.setattr(OpenAILLM, "generate", fake_generate)

    app = create_app()
    client = app.test_client()
    resp = client.post("/run", data={"date": "2025-08-09"})
    assert resp.status_code == 200
    assert resp.headers["Content-Type"].startswith("text/html")
    body = resp.get_data(as_text=True)
    assert "Deuteronomy 6:4-13" in body

