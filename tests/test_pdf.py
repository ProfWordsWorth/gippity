from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import types

from lectio_plus.app import OpenAILLM, create_app


def test_pdf_endpoint_works(monkeypatch) -> None:
    # Monkeypatch LLM to avoid network
    outputs = [
        "reflection",
        '{"title": "T", "artist": "A", "year": "2000", "image_url": "https://upload.wikimedia.org/x.jpg"}',
    ]

    def fake_generate(self, model, prompt, temperature=0.2, max_tokens=None):  # noqa: ARG001
        return outputs.pop(0)

    monkeypatch.setattr(OpenAILLM, "generate", fake_generate)
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    monkeypatch.setenv("OPENAI_BASE_URL", "http://localhost:11434/v1")
    monkeypatch.setenv("OPENAI_API_KEY", "ollama")

    # Provide a fake pdfkit module
    fake_pdfkit = types.SimpleNamespace()

    def from_string(html: str, out: bool, options=None):  # noqa: ARG001
        return b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n..."

    fake_pdfkit.from_string = from_string
    monkeypatch.setitem(sys.modules, "pdfkit", fake_pdfkit)

    app = create_app()
    client = app.test_client()
    resp = client.post("/pdf", data={"date": "2024-05-04"})
    assert resp.status_code == 200
    assert resp.headers["Content-Type"].startswith("application/pdf")
    body = resp.get_data()
    assert body.startswith(b"%PDF") and len(body) > 10
