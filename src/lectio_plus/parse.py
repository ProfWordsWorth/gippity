from __future__ import annotations

from dataclasses import dataclass
import re
from html.parser import HTMLParser
from typing import List


@dataclass
class Section:
    label: str
    citation: str
    text: str
    is_psalm: bool
    is_gospel: bool


class _TextExtractor(HTMLParser):
    """Simple HTML text extractor.

    Collects all text nodes in the order encountered. Each piece of
    significant text becomes a separate entry in ``texts``.
    """

    def __init__(self) -> None:
        super().__init__()
        self.texts: List[str] = []

    def handle_data(self, data: str) -> None:
        text = data.strip()
        if text:
            self.texts.append(text)


_READING_RE = re.compile(r"reading\s+[0-9ivxlcdm]+", re.IGNORECASE)


def _is_heading(text: str) -> bool:
    lt = text.strip().lower()
    return bool(_READING_RE.fullmatch(lt)) or lt in {"responsorial psalm", "gospel"}


def _looks_like_citation(text: str) -> bool:
    return ":" in text and bool(re.search(r"\d", text))


def extract_sections(html: str) -> List[Section]:
    parser = _TextExtractor()
    parser.feed(html)
    lines = parser.texts

    sections: List[Section] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if _is_heading(line):
            label = line
            lower = label.lower()
            is_psalm = lower == "responsorial psalm"
            is_gospel = lower == "gospel"
            i += 1
            citation = ""
            if i < len(lines) and _looks_like_citation(lines[i]):
                citation = lines[i]
                i += 1
            body_lines: List[str] = []
            while i < len(lines) and not _is_heading(lines[i]):
                body_lines.append(lines[i])
                i += 1
            text = "\n".join(body_lines).strip()
            sections.append(
                Section(
                    label=label,
                    citation=citation,
                    text=text,
                    is_psalm=is_psalm,
                    is_gospel=is_gospel,
                )
            )
        else:
            i += 1
    return sections


def build_readings_block(sections: List[Section]) -> str:
    blocks: List[str] = []
    for sec in sections:
        lines = [sec.label]
        if sec.citation:
            lines.append(sec.citation)
        if sec.text:
            lines.append(sec.text.strip())
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)
