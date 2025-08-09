import sys
from pathlib import Path

# Ensure src package is importable
sys.path.append(str(Path(__file__).resolve().parents[1] / 'src'))

from lectio_plus.parse import extract_sections, build_readings_block


def read_fixture(name: str) -> str:
    path = Path(__file__).resolve().parents[1] / 'fixtures' / 'usccb' / name
    return path.read_text(encoding='utf-8')


def test_extract_sections_basic():
    html = read_fixture('sample_1.html')
    sections = extract_sections(html)

    reading_sections = [s for s in sections if s.label.lower().startswith('reading')]
    psalm_sections = [s for s in sections if s.is_psalm]
    gospel_sections = [s for s in sections if s.is_gospel]

    assert len(reading_sections) == 1
    assert len(psalm_sections) == 1
    assert len(gospel_sections) == 1

    for sec in sections:
        assert sec.citation  # citation present

    assert psalm_sections[0].is_psalm and not psalm_sections[0].is_gospel
    assert gospel_sections[0].is_gospel and not gospel_sections[0].is_psalm


def test_build_readings_block_contains_sections():
    html = read_fixture('sample_1.html')
    sections = extract_sections(html)
    block = build_readings_block(sections)

    for sec in sections:
        assert sec.label in block
        assert sec.text.split('\n')[0] in block
