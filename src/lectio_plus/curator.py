"""Content curation helpers."""

from collections.abc import Iterable
import json
import re

import requests  # type: ignore[import-untyped]


def curate(parts: Iterable[str]) -> str:
    """Join ``parts`` with newlines."""
    return "\n".join(parts)


def parse_art_json(raw: str) -> dict:
    """Parse and validate ``raw`` JSON describing a work of art.

    Code fences are stripped before parsing.  The resulting object must contain
    non-empty string values for the keys ``title``, ``artist``, ``year`` and
    ``image_url``.  The ``image_url`` must begin with the Wikimedia upload
    domain.  :class:`ValueError` is raised on failure.
    """

    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```\w*\n?", "", text)
        text = text.rsplit("```", 1)[0].strip()

    try:
        data = json.loads(text)
    except Exception as exc:  # pragma: no cover - deliberately broad
        raise ValueError("invalid JSON") from exc

    required = ["title", "artist", "year", "image_url"]
    result: dict[str, str] = {}
    for key in required:
        value = data.get(key)
        if not isinstance(value, str) or not value.strip():
            raise ValueError("missing fields in art JSON")
        result[key] = value.strip()

    if not result["image_url"].startswith("https://upload.wikimedia.org/"):
        raise ValueError("image_url must be a Wikimedia upload URL")

    return result


def safe_parse_art_json(text: str) -> dict[str, str]:
    """Parse messy curator JSON and normalize fields.

    - Extract the first JSON object between ``{`` and the last ``}``.
    - Require string keys: ``title``, ``artist``, ``year``, ``image_url``.
    - If ``image_url`` is not an upload URL, attempt to resolve via
      :func:`ensure_upload_wikimedia_url`. If still invalid, raise ``ValueError``.
    """

    # First, try to parse the whole payload directly
    try:
        data_any = json.loads(text)
        if isinstance(data_any, list):
            # pick the first dict in the array
            data = next((item for item in data_any if isinstance(item, dict)), None)
            if data is None:
                raise ValueError("no object in array")
        elif isinstance(data_any, dict):
            data = data_any
        else:
            raise ValueError("unexpected JSON type")
    except Exception:
        # Fallback: find the first valid JSON object in the text using a
        # non‑greedy match and try to parse it.
        match = re.search(r"\{.*?\}", text, flags=re.S)
        if not match:
            raise ValueError("no JSON object found")
        obj_text = match.group(0)
        data = json.loads(obj_text)
    if isinstance(data, list):
        data = next((item for item in data if isinstance(item, dict)), None)
        if data is None:
            raise ValueError("no object in list")
    required = ["title", "artist", "year", "image_url"]
    out: dict[str, str] = {}
    for key in required:
        val = data.get(key)
        if not isinstance(val, str) or not val.strip():
            raise ValueError("missing fields in art JSON")
        out[key] = val.strip()

    if not out["image_url"].startswith("https://upload.wikimedia.org/"):
        resolved = ensure_upload_wikimedia_url(out["image_url"])
        if not isinstance(resolved, str) or not resolved.startswith(
            "https://upload.wikimedia.org/"
        ):
            raise ValueError("image_url must be a Wikimedia upload URL")
        out["image_url"] = resolved

    return out


def curator_fallback() -> dict[str, str]:
    """Return a known public-domain artwork as a safe fallback."""
    return {
        "title": "The Annunciation",
        "artist": "Fra Angelico",
        "year": "c. 1430–1432",
        "image_url": (
            "https://upload.wikimedia.org/wikipedia/commons/3/3d/"
            "Fra_Angelico_-_Annunciation_%28Prado%29.jpg"
        ),
    }


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


__all__ = [
    "curate",
    "parse_art_json",
    "safe_parse_art_json",
    "ensure_upload_wikimedia_url",
    "curator_fallback",
]
