"""Prompt building helpers."""

from __future__ import annotations


def build_prompt(text: str) -> str:
    """Return a simple prompt string incorporating *text*."""
    return f"Prompt: {text}"
