from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lectio_plus.html_build import build_prompt3_html, Section, strip_code_fences


def test_build_prompt3_html_basic() -> None:
    art = {
        "title": "Test Art",
        "artist": "Anon",
        "year": "1900",
        "image_url": "https://upload.wikimedia.org/test.jpg",
    }
    sections = [
        Section(heading="Reading 1", reading="In the beginning...", questions=["What stood out?"]),
    ]
    html_doc = build_prompt3_html("2024-05-04", art, sections, "Final reflection")
    assert html_doc.startswith("<!DOCTYPE html>")
    assert art["image_url"] in html_doc
    assert "```" not in html_doc


def test_strip_code_fences() -> None:
    text = "```markdown\nHere is the content:\nHello\n```"
    assert strip_code_fences(text) == "Hello"

