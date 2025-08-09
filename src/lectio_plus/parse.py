"""Parsing helpers for :mod:`lectio_plus`.

This module provides lightweight parsing utilities tailored for small HTML
snippets from the USCCB web site.  It intentionally avoids external
dependencies so the implementation can operate on the provided fixtures
without network access.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import List


@dataclass
class Section:
    """Represents one liturgical section from the USCCB readings page."""

    label: str
    citation: str
    text: str
    is_psalm: bool
    is_gospel: bool


_HEADING_RE = re.compile(
    r"^(reading\s*[1i]|responsorial psalm|gospel)", re.IGNORECASE
)


def _html_to_lines(html: str) -> List[str]:
    """Return a list of textual lines extracted from ``html``."""

    # Normalize a few block-level tags into newlines so we can work with plain
    # text.  This is *very* small‑scale and only needs to support our fixture.
    text = re.sub(r"(?i)<br\s*/?>", "\n", html)
    text = re.sub(r"(?i)</(p|div|h[1-6])>", "\n", text)
    text = re.sub(r"<[^>]+>", "", text)
    lines = [line.strip() for line in text.splitlines()]
    return [line for line in lines if line]


def _looks_like_citation(line: str) -> bool:
    """Return ``True`` if ``line`` resembles a scripture citation."""

    return bool(re.search(r"\d+:\d+", line))


def extract_sections(html: str) -> List[Section]:
    """Extract :class:`Section` objects from ``html``.

    The parser searches for headings such as ``Reading 1``, ``Responsorial
    Psalm`` and ``Gospel``.  The first scripture‑looking line after a heading is
    treated as the citation and the remaining lines up to the next heading make
    up the body of the section.
    """

    lines = _html_to_lines(html)
    sections: List[Section] = []
    current: Section | None = None
    body_lines: List[str] = []
    expecting_citation = False

    for line in lines:
        lower = line.lower()
        if _HEADING_RE.match(lower):
            # Close out the previous section if we were building one.
            if current is not None:
                current.text = "\n".join(body_lines).strip()
                sections.append(current)

            is_psalm = lower.startswith("responsorial psalm")
            is_gospel = lower.startswith("gospel")
            current = Section(line, "", "", is_psalm, is_gospel)
            body_lines = []
            expecting_citation = True
            continue

        if current is not None:
            if expecting_citation:
                # The first non-heading line is assumed to be a citation.  If it
                # does not look like a citation, we still treat it as one.
                if _looks_like_citation(line) or not current.citation:
                    current.citation = line
                    expecting_citation = False
                    continue

            body_lines.append(line)

    if current is not None:
        current.text = "\n".join(body_lines).strip()
        sections.append(current)

    return sections


def build_readings_block(sections: List[Section]) -> str:
    """Build a single string containing all sections in order."""

    blocks = []
    for sec in sections:
        lines = [sec.label]
        if sec.citation:
            lines.append(sec.citation)
        if sec.text:
            lines.append(sec.text)
        blocks.append("\n".join(lines))

    return "\n\n".join(blocks).strip()


def parse_usccb_html(html: str) -> str:
    """Parse ``html`` and return a human readable readings block."""

    sections = extract_sections(html)
    return build_readings_block(sections)


__all__ = [
    "parse_usccb_html",
    "Section",
    "extract_sections",
    "build_readings_block",
]

