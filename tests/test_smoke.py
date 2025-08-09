from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pkg import hello


def test_smoke() -> None:
    assert hello() == "hello"
