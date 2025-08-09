"""Content curation helpers."""

from __future__ import annotations

from typing import Iterable, TypeVar

T = TypeVar("T")


def unique(items: Iterable[T]) -> list[T]:
    """Return a list of unique items, preserving order."""
    seen: set[T] = set()
    result: list[T] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result
