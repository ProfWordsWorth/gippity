from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lectio_plus.prompts import BASE_PROMPT


def test_base_prompt_defined() -> None:
    assert isinstance(BASE_PROMPT, str)
    assert BASE_PROMPT
