"""Very small in-memory cache implementation."""

from __future__ import annotations


class SimpleCache:
    """A tiny in-memory cache."""

    def __init__(self) -> None:
        self._store: dict[str, str] = {}

    def get(self, key: str) -> str | None:
        """Retrieve a value from the cache."""
        return self._store.get(key)

    def set(self, key: str, value: str) -> None:
        """Store a value in the cache."""
        self._store[key] = value
