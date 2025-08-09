from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict


@dataclass
class Response:
    data: str
    status_code: int = 200
    mimetype: str | None = None

    def get_data(self, as_text: bool = False):
        return self.data if as_text else self.data.encode()


class _Request:
    def __init__(self) -> None:
        self.form: Dict[str, str] = {}


request = _Request()


class Flask:
    def __init__(self, name: str) -> None:
        self.name = name
        self._routes: Dict[tuple[str, str], Callable[[], Any]] = {}
        self.config: Dict[str, Any] = {}

    def get(self, path: str) -> Callable[[Callable[[], Any]], Callable[[], Any]]:
        def decorator(func: Callable[[], Any]) -> Callable[[], Any]:
            self._routes[("GET", path)] = func
            return func

        return decorator

    def post(self, path: str) -> Callable[[Callable[[], Any]], Callable[[], Any]]:
        def decorator(func: Callable[[], Any]) -> Callable[[], Any]:
            self._routes[("POST", path)] = func
            return func

        return decorator

    def test_client(self) -> Any:
        app = self

        class Client:
            def get(self, path: str) -> Response:
                request.form = {}
                func = app._routes.get(("GET", path))
                if func is None:
                    return Response("", 404)
                rv = func()
                return rv if isinstance(rv, Response) else Response(rv)

            def post(self, path: str, data: Dict[str, str] | None = None) -> Response:
                request.form = data or {}
                func = app._routes.get(("POST", path))
                if func is None:
                    return Response("", 404)
                rv = func()
                return rv if isinstance(rv, Response) else Response(rv)

        return Client()

    def run(self, host: str = "127.0.0.1", port: int = 5000) -> None:
        print(f"* Running on http://{host}:{port} (stub Flask server)")


__all__ = ["Flask", "Response", "request"]
