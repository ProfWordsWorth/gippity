"""Tests for :mod:`lectio_plus.curator`."""

from pathlib import Path
import importlib
import sys

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import lectio_plus.curator as curator


class FakeResponse:
    """Lightweight stand-in for :class:`requests.Response`."""

    def __init__(self, url: str, status_code: int) -> None:
        self.url = url
        self.status_code = status_code

    @property
    def ok(self) -> bool:  # pragma: no cover - trivial
        return 200 <= self.status_code < 400


def test_curate_joins_parts() -> None:
    result = curator.curate(["a", "b"])
    assert result == "a\nb"


def test_ensure_upload_wikimedia_url_direct(monkeypatch) -> None:
    url = "https://upload.wikimedia.org/wikipedia/commons/f/ff/Test.jpg"

    def fail(*_args, **_kwargs):  # pragma: no cover - should never be called
        raise AssertionError("network call not expected")

    monkeypatch.setattr(requests, "head", fail)
    monkeypatch.setattr(requests, "get", fail)

    assert curator.ensure_upload_wikimedia_url(url) == url


def test_ensure_upload_wikimedia_url_resolves(monkeypatch) -> None:
    start = "https://commons.wikimedia.org/wiki/Special:FilePath/Foo.jpg"
    final = "https://upload.wikimedia.org/wikipedia/commons/f/ff/Foo.jpg"

    def fake_head(*_args, **_kwargs):
        raise requests.RequestException("HEAD not supported")

    def fake_get(*_args, **_kwargs):
        return FakeResponse(final, 200)

    monkeypatch.setattr(requests, "head", fake_head)
    monkeypatch.setattr(requests, "get", fake_get)

    assert curator.ensure_upload_wikimedia_url(start) == final


def test_ensure_upload_wikimedia_url_non_commons(monkeypatch) -> None:
    url = "https://example.com/image.jpg"

    def fake_head(*_args, **_kwargs):
        return FakeResponse(url, 200)

    def fail_get(*_args, **_kwargs):  # pragma: no cover - should never be called
        raise AssertionError("GET should not be called")

    monkeypatch.setattr(requests, "head", fake_head)
    monkeypatch.setattr(requests, "get", fail_get)

    assert curator.ensure_upload_wikimedia_url(url) == url


def test_ensure_upload_wikimedia_url_uses_real_requests() -> None:
    url = "https://upload.wikimedia.org/x.jpg"
    assert curator.ensure_upload_wikimedia_url(url) == url
    real_requests = importlib.import_module("requests")
    assert curator.requests is real_requests
    assert "site-packages" in Path(real_requests.__file__).parts

