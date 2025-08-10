from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import requests

from lectio_plus import scrape


class FakeResp:
    def __init__(self, text: str, url: str = "") -> None:
        self.text = text
        self.url = url

    def raise_for_status(self) -> None:
        return None


def test_fetch_usccb_formats_url_and_caches(monkeypatch, tmp_path) -> None:
    html = Path("fixtures/usccb/sample_1.html").read_text(encoding="utf-8")
    captured = {}

    def fake_get(url, headers=None, timeout=None):  # noqa: ARG001
        captured["url"] = url
        return FakeResp(html, url)

    monkeypatch.setattr(requests, "get", fake_get)
    # First call hits fake_get
    text1, url1 = scrape.fetch_usccb("2025-08-09")
    assert "20250809.cfm" in url1
    assert text1.startswith("<html")
    # Second call should use cache and not call fake_get again
    captured["url"] = None
    text2, url2 = scrape.fetch_usccb("2025-08-09")
    assert text2 == text1
    assert url2 == url1
    assert captured["url"] is None
