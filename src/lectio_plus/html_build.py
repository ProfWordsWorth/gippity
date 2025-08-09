"""HTML building helpers."""


def build_html(body: str) -> str:
    """Wrap ``body`` in a minimal HTML page."""
    return f"<html><body>{body}</body></html>"


__all__ = ["build_html"]
