"""Utilities for fetching remote content."""

from __future__ import annotations


def fetch(url: str) -> str:
    """Return a placeholder string representing fetched content."""
    return f"<html><title>{url}</title></html>"
