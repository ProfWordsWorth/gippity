"""Prompt definitions for :mod:`lectio_plus`.

This module centralizes all template strings used by the lectio-plus
application.  Each template contains placeholders that are filled by the
helper functions defined below.
"""

from __future__ import annotations


PROMPT_1 = (
    "CATHOLIC DAILY LECTIO-PLUS MODULE\n"
    "Use the following lectionary readings as the basis for a brief, clear "
    "reflection.\n\n"
    "<<READINGS>>"
)


PROMPT_2 = (
    "You are an art curator who responds strictly in JSON.\n"
    "Given the date <<DATE>> and the scripture passages below, suggest "
    "relevant works of art.  Return a JSON array where each item has the "
    "keys 'title', 'artist', 'year', and 'reason'.  Do not include any extra "
    "fields or commentary.\n\n"
    "<<READINGS>>"
)


PROMPT_3 = (
    "Build an HTML fragment for a daily lectio page.\n"
    "Insert the date in an <h1> element and arrange the provided blocks in "
    "separate <section> elements.\n\n"
    "Date: <<DATE>>\n"
    "Blocks:\n"
    "<<RAW_BLOCKS>>"
)


# New: Section enrichment prompt to produce context, exegesis, questions
PROMPT_SECTIONS = (
    "You are a Catholic theologian and catechist.\n"
    "Given the following lectionary sections for the date <<DATE>>, write:\n"
    "- A 1–2 sentence Context for each section (<= 50 words).\n"
    "- An optional 1 sentence Exegetical Note (<= 40 words).\n"
    "- 3–4 concise Reflection Questions per section.\n"
    "- A short Final Reflection covering all readings (<= 120 words).\n"
    "Respond strictly in JSON with keys: {\"sections\": [\n"
    "  {\"heading\": str, \"context\": str, \"exegesis\": str | null, \"questions\": [str, ...]}\n"
    "], \"final_reflection\": str}. No HTML, no backticks, no commentary.\n\n"
    "SECTIONS INPUT (in order):\n"
    "<<SECTIONS>>\n"
)


def make_prompt1(readings_block: str) -> str:
    """Insert ``readings_block`` into :data:`PROMPT_1`."""

    return PROMPT_1.replace("<<READINGS>>", readings_block)


def make_prompt2(date_str: str, readings_block: str) -> str:
    """Insert ``date_str`` and truncated ``readings_block`` into
    :data:`PROMPT_2`.

    The ``readings_block`` is truncated to 8,000 characters to keep the
    resulting prompt at a manageable size.
    """

    truncated = readings_block[:8000]
    return (
        PROMPT_2.replace("<<DATE>>", date_str).replace("<<READINGS>>", truncated)
    )


def make_prompt3(date_str: str, raw_blocks: str) -> str:
    """Insert ``date_str`` and ``raw_blocks`` into :data:`PROMPT_3`."""

    return (
        PROMPT_3.replace("<<DATE>>", date_str).replace("<<RAW_BLOCKS>>", raw_blocks)
    )


def make_prompt_sections(date_str: str, sections_text: str) -> str:
    """Insert ``date_str`` and ``sections_text`` into :data:`PROMPT_SECTIONS`."""

    truncated = sections_text[:12000]
    return (
        PROMPT_SECTIONS.replace("<<DATE>>", date_str).replace("<<SECTIONS>>", truncated)
    )


__all__ = [
    "PROMPT_1",
    "PROMPT_2",
    "PROMPT_3",
    "PROMPT_SECTIONS",
    "make_prompt1",
    "make_prompt2",
    "make_prompt3",
    "make_prompt_sections",
]
