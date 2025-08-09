"""Content curation helpers."""

from collections.abc import Iterable

import requests  # type: ignore[import-untyped]


def curate(parts: Iterable[str]) -> str:
    """Join ``parts`` with newlines."""
    return "\n".join(parts)


def ensure_upload_wikimedia_url(
    url: str, *, follow_redirects: bool = True
) -> str:
    """Resolve ``url`` to the Wikimedia upload domain if possible.

    If ``url`` already points to the ``upload.wikimedia.org`` domain it is
    returned unchanged. Otherwise, the URL is resolved by first attempting a
    ``HEAD`` request. Some endpoints (notably ``Special:FilePath``) may not
    support ``HEAD`` requests, so a ``GET`` request is attempted if the ``HEAD``
    request fails. If the final resolved URL begins with the Wikimedia upload
    domain it is returned; otherwise the original ``url`` is returned.
    """

    prefix = "https://upload.wikimedia.org/"
    if url.startswith(prefix):
        return url

    try:
        resp = requests.head(url, allow_redirects=follow_redirects, timeout=10)
    except Exception:
        resp = None

    if resp is None or not getattr(resp, "ok", False):
        try:
            resp = requests.get(url, allow_redirects=follow_redirects, timeout=10)
        except Exception:
            resp = None

    if resp is not None:
        final_url = getattr(resp, "url", url)
        if isinstance(final_url, str) and final_url.startswith(prefix):
            return final_url

    return url


__all__ = ["curate", "ensure_upload_wikimedia_url"]
