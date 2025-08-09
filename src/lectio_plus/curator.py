"""Content curation helpers."""

from collections.abc import Iterable


def curate(parts: Iterable[str]) -> str:
    """Join ``parts`` with newlines."""
    return "\n".join(parts)


__all__ = ["curate"]
