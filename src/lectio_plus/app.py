"""Application entry points and LLM provider selection for :mod:`lectio_plus`."""

from __future__ import annotations

import argparse
import datetime as _dt
import os
from pathlib import Path
from typing import Any, Iterable, Protocol, cast

from flask import Flask, request  # type: ignore[import-not-found]

from . import prompts
from .curator import curate, parse_art_json
from .html_build import build_html
from .parse import parse_usccb_html


def _ollama_timeout() -> float:
    """Return Ollama timeout in seconds (default 120, override via OLLAMA_TIMEOUT)."""
    return float(os.getenv("OLLAMA_TIMEOUT", "120"))


class LLM(Protocol):
    """Minimal interface implemented by language model providers."""

    def generate(
        self,
        model: str,
        prompt: str,
        temperature: float = 0.2,
        max_tokens: int | None = None,
    ) -> str:
        """Return a completion for ``prompt``."""


class FakeLLM:
    """Offline stand‑in returning canned responses for the three prompts."""

    def generate(
        self,
        model: str,
        prompt: str,
        temperature: float = 0.2,
        max_tokens: int | None = None,
    ) -> str:
        if "Build an HTML fragment" in prompt:
            return "<section>stub html</section>"
        if "art curator" in prompt:
            return (
                "{\"title\": \"Test Art\", \"artist\": \"Anon\", "
                "\"year\": \"1900\", \"image_url\": "
                "\"https://upload.wikimedia.org/test.jpg\"}"
            )
        return "stub reflection"


class OpenAILLM:
    """Thin wrapper around the official OpenAI Python SDK."""

    def __init__(self, base_url: str | None, api_key: str) -> None:
        self._base_url = base_url
        self._api_key = api_key

    def generate(
        self,
        model: str,
        prompt: str,
        temperature: float = 0.2,
        max_tokens: int | None = None,
    ) -> str:
        from openai import OpenAI  # type: ignore[import-not-found]

        client = OpenAI(base_url=self._base_url, api_key=self._api_key, timeout=10.0)

        provider = os.environ.get("LLM_PROVIDER")
        base_url = os.environ.get("OPENAI_BASE_URL") or self._base_url or ""
        is_ollama = (
            provider == "ollama"
            or base_url.startswith("http://localhost:11434")
            or base_url.startswith("https://localhost:11434")
        )

        if is_ollama:
            # Recreate client for Ollama with configurable timeout
            chat_client = OpenAI(
                base_url=base_url,
                api_key=self._api_key,
                timeout=_ollama_timeout(),
            )
            msgs: list[dict[str, str]] = [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt},
            ]
            if max_tokens is None:
                resp_chat = chat_client.chat.completions.create(
                    model=model,
                    messages=cast(Any, msgs),
                    temperature=temperature,
                    timeout=_ollama_timeout(),
                )
            else:
                resp_chat = chat_client.chat.completions.create(
                    model=model,
                    messages=cast(Any, msgs),
                    temperature=temperature,
                    max_tokens=max_tokens,
                    timeout=_ollama_timeout(),
                )
            return resp_chat.choices[0].message.content or ""

        resp = client.responses.create(
            model=model,
            input=prompt,
            temperature=temperature,
            max_output_tokens=max_tokens,
        )
        return resp.output_text


def get_llm() -> LLM:
    """Return an :class:`LLM` implementation based on environment variables."""

    provider = os.environ.get("LLM_PROVIDER")
    if provider == "ollama":
        base_url = os.environ.get("OPENAI_BASE_URL")
        api_key = os.environ.get("OPENAI_API_KEY", "")
        if base_url != "http://localhost:11434/v1" or not api_key:
            raise RuntimeError("OLLAMA requires OPENAI_BASE_URL and OPENAI_API_KEY")
        return OpenAILLM(base_url, api_key)
    return FakeLLM()


def stitch_blocks_for_prompt3(blocks: Iterable[str]) -> str:
    """Join ``blocks`` for inclusion in :func:`prompts.make_prompt3`."""

    return curate(list(blocks))


def inject_cover_metadata(html: str, date_str: str, art: dict[str, str]) -> str:
    """Replace placeholder strings in ``html`` with ``date_str`` and ``art``."""

    return (
        html.replace("Current Date", date_str)
        .replace("Cover Title", art["title"])
        .replace("Cover Artist", art["artist"])
        .replace("Cover Year", art["year"])
        .replace("cid:cover.jpg", art["image_url"])
    )


def run(readings_block: str, date_str: str = "DATE") -> str:
    """Generate HTML for ``readings_block`` using the configured LLM provider."""

    llm = get_llm()
    reflection_model = os.environ.get("REFLECTION_MODEL", "gpt-5-chat-latest")
    art_model = os.environ.get("ART_MODEL", "gpt-5-mini")
    html_model = os.environ.get("HTML_MODEL", "gpt-5-mini")

    prompt1 = prompts.make_prompt1(readings_block)
    reflection = llm.generate(reflection_model, prompt1)

    prompt2 = prompts.make_prompt2(date_str, readings_block)
    art_raw = llm.generate(art_model, prompt2)
    art = parse_art_json(art_raw)
    art_block = curate([art["title"], art["artist"], art["year"], art["image_url"]])

    raw_blocks = stitch_blocks_for_prompt3([reflection, art_block])
    prompt3 = prompts.make_prompt3(date_str, raw_blocks)
    injected_html = llm.generate(html_model, prompt3)
    final_html = inject_cover_metadata(injected_html, date_str, art)
    return build_html(final_html)


def create_app(*, default_date: str | None = None) -> Flask:
    """Return a configured :class:`~flask.Flask` application."""

    app = Flask(__name__)
    app.config["DEFAULT_DATE"] = default_date

    @app.get("/")
    def index() -> str:
        today = _dt.date.today().isoformat()
        value = app.config.get("DEFAULT_DATE") or today
        return (
            "<form method='post' action='/run'>"
            f"<input type='date' name='date' value='{value}'>"
            "<button type='submit'>Generate</button>"
            "</form>"
        )

    @app.post("/run")
    def run_route() -> tuple[str, int, dict[str, str]]:
        date_str = request.form.get("date") or app.config.get("DEFAULT_DATE")
        if not date_str:
            date_str = _dt.date.today().isoformat()

        fixture_path = Path(__file__).resolve().parents[2] / "fixtures" / "usccb" / "sample_1.html"
        sample_html = fixture_path.read_text(encoding="utf-8")
        readings_block = parse_usccb_html(sample_html)
        html = run(readings_block, date_str)
        return html, 200, {"Content-Type": "text/html; charset=utf-8"}

    return app


def main(argv: Iterable[str] | None = None) -> int:
    """Simple command line interface for the application."""

    parser = argparse.ArgumentParser()
    parser.add_argument("--serve", action="store_true", help="run the web server")
    parser.add_argument("--date", help="ISO date for generation")
    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.serve:
        app = create_app(default_date=args.date)
        app.run(host="127.0.0.1", port=5057)
        return 0

    fixture_path = Path(__file__).resolve().parents[2] / "fixtures" / "usccb" / "sample_1.html"
    sample_html = fixture_path.read_text(encoding="utf-8")
    readings_block = parse_usccb_html(sample_html)
    date_str = args.date or _dt.date.today().isoformat()
    html = run(readings_block, date_str)
    print(html)
    return 0


__all__ = [
    "LLM",
    "FakeLLM",
    "OpenAILLM",
    "get_llm",
    "stitch_blocks_for_prompt3",
    "inject_cover_metadata",
    "run",
    "create_app",
    "main",
]


if __name__ == "__main__":  # pragma: no cover - manual invocation
    raise SystemExit(main())
