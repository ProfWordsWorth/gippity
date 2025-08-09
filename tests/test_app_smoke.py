from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lectio_plus.app import run


def test_app_run_returns_html() -> None:
    html = run("Hi")
    assert html.startswith("<html>")
    assert html.endswith("</html>")
