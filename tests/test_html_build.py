from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lectio_plus.html_build import build_html


def test_build_html_wraps_body() -> None:
    html = build_html("Hello")
    assert "<body>Hello</body>" in html
