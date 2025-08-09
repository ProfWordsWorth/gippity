"""Application entry points for :mod:`lectio_plus`."""

from .html_build import build_html


def run(text: str) -> str:
    """Return a simple HTML page containing ``text``."""
    return build_html(text)


__all__ = ["run"]
