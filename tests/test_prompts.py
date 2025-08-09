"""Tests for :mod:`lectio_plus.prompts`."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lectio_plus.prompts import (  # noqa: E402  (import after sys.path tweak)
    PROMPT_1,
    PROMPT_2,
    PROMPT_3,
    make_prompt1,
    make_prompt2,
    make_prompt3,
)


def test_make_prompt1_inserts_readings() -> None:
    block = "First reading"
    result = make_prompt1(block)
    assert block in result
    assert "<<READINGS>>" not in result


def test_prompts_defined() -> None:
    assert isinstance(PROMPT_1, str) and PROMPT_1
    assert isinstance(PROMPT_2, str) and PROMPT_2
    assert isinstance(PROMPT_3, str) and PROMPT_3


def test_make_prompt2_truncates_and_fills() -> None:
    long_text = "R" * 9000
    date_str = "2024-05-18"
    result = make_prompt2(date_str, long_text)
    assert date_str in result
    assert "<<DATE>>" not in result
    assert "<<READINGS>>" not in result
    assert "R" * 8000 in result
    assert "R" * 8001 not in result


def test_make_prompt3_inserts_blocks() -> None:
    date_str = "2024-05-18"
    blocks = "<p>Content</p>"
    result = make_prompt3(date_str, blocks)
    assert date_str in result
    assert blocks in result
    assert "<<DATE>>" not in result
    assert "<<RAW_BLOCKS>>" not in result


def test_no_smart_apostrophe() -> None:
    text = Path("src/lectio_plus/prompts.py").read_text(encoding="utf-8")
    assert "\u2019" not in text

