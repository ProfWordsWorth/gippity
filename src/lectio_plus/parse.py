"""Parsing helpers."""

from __future__ import annotations

import re


def extract_title(html: str) -> str:
    """Extract the contents of the first <title> tag in *html*.

    The function is intentionally tiny; it is sufficient for tests and
    demonstrations.
    """
    match = re.search(r"<title>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
    return match.group(1).strip() if match else ""
