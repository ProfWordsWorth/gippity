from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lectio_plus.parse import parse_usccb_html


def test_parse_sample() -> None:
    sample = Path("fixtures/usccb/sample_1.html").read_text()
    result = parse_usccb_html(sample)
    assert "Sample 1" in result
