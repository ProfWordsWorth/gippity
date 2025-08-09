from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lectio_plus.curator import curate


def test_curate_joins_parts() -> None:
    result = curate(["a", "b"])
    assert result == "a\nb"
