"""Scraping utilities for USCCB readings with simple caching."""

from __future__ import annotations

import os
import time
from typing import Tuple

import requests  # type: ignore[import-untyped]

from .cache import SimpleCache

_cache = SimpleCache()
_TTL_SECONDS = 3 * 60 * 60


def fetch_usccb(date_str: str) -> Tuple[str, str]:
    """Fetch USCCB readings HTML for ``date_str`` (YYYY-MM-DD).

    Returns a tuple of ``(html_text, url)``. Results are cached for ~3 hours.
    """

    yyyymmdd = date_str.replace("-", "")
    base = os.getenv("USCCB_BASE_URL", "https://bible.usccb.org/bible/readings/")
    if not base.endswith("/"):
        base = base + "/"
    url = f"{base}{yyyymmdd}.cfm"

    now = time.time()
    cache_key = f"usccb:{yyyymmdd}"
    cached = _cache.get(cache_key)
    if isinstance(cached, dict):
        exp = cached.get("exp")
        if isinstance(exp, (int, float)) and exp > now and "text" in cached and "url" in cached:
            return str(cached["text"]), str(cached["url"])

    headers = {"User-Agent": "lectio-plus/1.0"}
    try:
        resp = requests.get(url, headers=headers, timeout=(5, 20))
        resp.raise_for_status()
        data = {"text": resp.text, "url": url, "exp": now + _TTL_SECONDS}
    except Exception:
        daily_base = os.getenv("USCCB_DAILY_URL", "https://bible.usccb.org/daily-bible-reading")
        alt_url = f"{daily_base}?date={date_str}"
        resp = requests.get(alt_url, headers=headers, timeout=(5, 20))
        resp.raise_for_status()
        data = {"text": resp.text, "url": alt_url, "exp": now + _TTL_SECONDS}
    _cache.set(cache_key, data)
    return data["text"], data["url"]


__all__ = ["fetch_usccb"]
