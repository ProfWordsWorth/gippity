"""Parsing helpers for :mod:`lectio_plus`."""


def parse_usccb_html(html: str) -> str:
    """Return the raw ``html`` for now.

    The real project would parse the input, but the placeholder simply returns
    it unchanged.
    """
    return html


__all__ = ["parse_usccb_html"]
