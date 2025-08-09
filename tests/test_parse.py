from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lectio_plus.parse import build_readings_block, extract_sections


def test_extract_and_build() -> None:
    html = Path("fixtures/usccb/sample_1.html").read_text()
    sections = extract_sections(html)

    readings = [s for s in sections if s.label.lower().startswith("reading")]
    psalms = [s for s in sections if s.is_psalm]
    gospels = [s for s in sections if s.is_gospel]

    assert len(readings) == 1
    assert len(psalms) == 1
    assert len(gospels) == 1

    reading = readings[0]
    psalm = psalms[0]
    gospel = gospels[0]

    assert reading.citation == "Deuteronomy 6:4-13"
    assert psalm.citation == "Psalm 18:2-3, 3-4, 47 and 51"
    assert gospel.citation == "Matthew 17:14-20"

    assert not reading.is_psalm and not reading.is_gospel
    assert psalm.is_psalm and not psalm.is_gospel
    assert gospel.is_gospel and not gospel.is_psalm

    block = build_readings_block(sections)
    for section in (reading, psalm, gospel):
        assert section.label in block
        assert section.text in block

