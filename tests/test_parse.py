from pathlib import Path

from lectio_plus.parse import extract_title


def test_extract_title() -> None:
    html = Path("fixtures/usccb/sample_1.html").read_text(encoding="utf-8")
    assert extract_title(html) == "Sample Title"
