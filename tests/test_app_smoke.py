from pathlib import Path

from lectio_plus.app import run


def test_app_smoke() -> None:
    path = Path("fixtures/usccb/sample_1.html")
    result = run(path)
    assert "<title>Sample Title</title>" in result
