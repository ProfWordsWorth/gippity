"""Tests for :mod:`lectio_plus.curator`."""

from pathlib import Path
from types import SimpleNamespace
import sys

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import lectio_plus.curator as curator


def test_curate_joins_parts() -> None:
    result = curator.curate(["a", "b"])
    assert result == "a\nb"


def test_ensure_upload_wikimedia_url_direct(monkeypatch) -> None:
    url = "https://upload.wikimedia.org/wikipedia/commons/f/ff/Test.jpg"

    def fail(*_args, **_kwargs):  # pragma: no cover - should never be called
        raise AssertionError("network call not expected")

    monkeypatch.setattr(curator.requests, "head", fail)
    monkeypatch.setattr(curator.requests, "get", fail)

    assert curator.ensure_upload_wikimedia_url(url) == url


def test_ensure_upload_wikimedia_url_resolves(monkeypatch) -> None:
    start = "https://commons.wikimedia.org/wiki/Special:FilePath/Foo.jpg"
    final = "https://upload.wikimedia.org/wikipedia/commons/f/ff/Foo.jpg"

    def fake_head(*_args, **_kwargs):
        raise requests.RequestException("HEAD not supported")

    def fake_get(*_args, **_kwargs):
        return SimpleNamespace(url=final, ok=True)

    monkeypatch.setattr(curator.requests, "head", fake_head)
    monkeypatch.setattr(curator.requests, "get", fake_get)

    assert curator.ensure_upload_wikimedia_url(start) == final


def test_ensure_upload_wikimedia_url_non_commons(monkeypatch) -> None:
    url = "https://example.com/image.jpg"

    def fake_head(*_args, **_kwargs):
        return SimpleNamespace(url=url, ok=True)

    def fail_get(*_args, **_kwargs):  # pragma: no cover - should never be called
        raise AssertionError("GET should not be called")

    monkeypatch.setattr(curator.requests, "head", fake_head)
    monkeypatch.setattr(curator.requests, "get", fail_get)

    assert curator.ensure_upload_wikimedia_url(url) == url

