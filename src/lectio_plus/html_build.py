"""HTML generation helpers."""

from __future__ import annotations


def build_html(title: str, body: str) -> str:
    """Return a minimal HTML page containing *title* and *body*."""
    return f"<html><head><title>{title}</title></head><body>{body}</body></html>"
