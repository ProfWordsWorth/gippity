"""Minimal stand-in for :mod:`requests` used in tests.

This module provides just enough of the ``requests`` API for the test suite to
patch ``head`` and ``get`` calls and to raise ``RequestException``. The real
``requests`` package is not available in this execution environment, so these
placeholders ensure imports succeed without performing any network I/O.
"""


class RequestException(Exception):
    """Exception raised when an HTTP request fails."""


def head(*_args, **_kwargs):  # pragma: no cover - never called in tests
    """Placeholder for :func:`requests.head`.

    The tests monkeypatch this function, so the implementation is never
    executed. It is defined here solely so that code importing ``requests`` can
    reference it.
    """

    raise RequestException("requests.head is not implemented")


def get(*_args, **_kwargs):  # pragma: no cover - never called in tests
    """Placeholder for :func:`requests.get`.

    The tests monkeypatch this function, so the implementation is never
    executed. It is defined here solely so that code importing ``requests`` can
    reference it.
    """

    raise RequestException("requests.get is not implemented")


__all__ = ["RequestException", "head", "get"]

