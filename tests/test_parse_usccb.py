from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lectio_plus.parse import parse_usccb_html


def test_parse_usccb_html_sections() -> None:
    html = Path("fixtures/usccb/sample_1.html").read_text(encoding="utf-8")
    sections = parse_usccb_html(html)
    labels = [s.label for s in sections]
    assert any(lab.lower().startswith("reading") for lab in labels)
    assert any(lab.lower().startswith("responsorial psalm") for lab in labels)
    assert any(lab.lower().startswith("gospel") for lab in labels)
    # Ensure text is non-empty for key sections
    for s in sections:
        if s.label.lower().startswith(("reading", "responsorial psalm", "gospel")):
            assert s.text
