"""A tiny in-memory cache."""

from typing import Any


class SimpleCache:
    """A minimal cache storing values in a dictionary."""

    def __init__(self) -> None:
        self._store: dict[str, Any] = {}

    def get(self, key: str) -> Any | None:
        """Retrieve a cached value."""
        return self._store.get(key)

    def set(self, key: str, value: Any) -> None:
        """Store ``value`` under ``key``."""
        self._store[key] = value


__all__ = ["SimpleCache"]
