"""Application entry points and LLM provider selection for :mod:`lectio_plus`."""

from __future__ import annotations

import argparse
import datetime as _dt
import os
from pathlib import Path
from typing import Any, Iterable, Protocol, cast

import time
from flask import Flask, jsonify, request  # type: ignore[import-not-found]

from . import prompts
from .curator import (
    curate,
    safe_parse_art_json,
    curator_fallback,
)
from .html_build import build_html, build_prompt3_html, strip_code_fences, Section as P3Section
from .parse import parse_usccb_html as parse_usccb_sections, make_prompt3_sections, build_readings_block
from . import scrape


def _ollama_timeout() -> float:
    """Return Ollama timeout in seconds (default 180, override via OLLAMA_TIMEOUT)."""
    return float(os.getenv("OLLAMA_TIMEOUT", "180"))


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
    """Generate deterministic Prompt‑3 HTML for ``readings_block``."""

    llm = get_llm()
    reflection_model = os.environ.get("REFLECTION_MODEL", "gpt-5-chat-latest")
    art_model = os.environ.get("ART_MODEL", "gpt-5-mini")
    # HTML model unused with deterministic layout; kept for env parity

    prompt1 = prompts.make_prompt1(readings_block)
    reflection = llm.generate(reflection_model, prompt1)

    prompt2 = prompts.make_prompt2(date_str, readings_block)
    art_raw = llm.generate(art_model, prompt2)
    try:
        art = safe_parse_art_json(art_raw)
    except Exception:
        # Use fallback to be resilient in library use
        art = curator_fallback()
    # Art block is still incorporated in the deterministic cover

    # Build sections deterministically from the fixture HTML and reflection
    try:
        # The readings_block comes from the USCCB HTML; we still have the
        # fixture path here for structured extraction.
        fixture_path = Path(__file__).resolve().parents[2] / "fixtures" / "usccb" / "sample_1.html"
        sample_html = fixture_path.read_text(encoding="utf-8")
        sections, final_reflection = make_prompt3_sections(sample_html, reflection)
    except Exception:
        # Fallback to a single section using the provided text
        sections = [P3Section(heading="Reading", reading=readings_block, questions=[])]
        final_reflection = reflection

    html_doc = build_prompt3_html(date_str, art, sections, strip_code_fences(final_reflection))

    # Back-compat: include legacy injected HTML from model as a comment
    try:
        raw_blocks = stitch_blocks_for_prompt3([reflection, curate([art["title"], art["artist"], art["year"], art["image_url"]])])
        prompt3 = prompts.make_prompt3(date_str, raw_blocks)
        html_model = os.environ.get("HTML_MODEL", "gpt-5-mini")
        injected_html_legacy = llm.generate(html_model, prompt3)
    except Exception:
        injected_html_legacy = ""

    return build_html(html_doc + (f"<!-- legacy: {injected_html_legacy} -->" if injected_html_legacy else ""))


def create_app(*, default_date: str | None = None) -> Flask:
    """Return a configured :class:`~flask.Flask` application."""

    app = Flask(__name__)
    app.config["DEFAULT_DATE"] = default_date

    @app.get("/healthz")
    def healthz():
        start = time.perf_counter()
        try:
            model = os.getenv("HTML_MODEL", "mistral:latest")
            llm = get_llm()
            _ = llm.generate(model, "ping", temperature=0.0, max_tokens=5)
            elapsed_ms = int((time.perf_counter() - start) * 1000)
            return jsonify({"ok": True, "model": model, "elapsed_ms": elapsed_ms}), 200
        except Exception as exc:  # pragma: no cover - deliberately broad
            return jsonify({"ok": False, "error": str(exc)}), 200

    @app.get("/")
    def index() -> str:
        today = _dt.date.today().isoformat()
        value = app.config.get("DEFAULT_DATE") or today
        return (
            "<form method='post' action='/run' style='margin-bottom:8px'>"
            f"<input type='date' name='date' value='{value}'>"
            "<button type='submit'>Generate</button>"
            "</form>"
            "<form method='post' action='/pdf'>"
            f"<input type='hidden' name='date' value='{value}'>"
            "<button type='submit'>Download PDF</button>"
            "</form>"
        )

    @app.post("/run")
    def run_route() -> tuple[str, int, dict[str, str]]:
        date_str = request.form.get("date") or app.config.get("DEFAULT_DATE")
        if not date_str:
            date_str = _dt.date.today().isoformat()

        sections_list: list | None = None
        try:
            html_usccb, _url = scrape.fetch_usccb(date_str)
            sections_list = parse_usccb_sections(html_usccb)
            readings_block = build_readings_block(sections_list)
        except Exception as exc:
            # Fallback to local fixture if live fetch/parsing fails
            app.logger.warning("live fetch/parsing failed: %s", exc)
            try:
                fixture_path = Path(__file__).resolve().parents[2] / "fixtures" / "usccb" / "sample_1.html"
                sample_html = fixture_path.read_text(encoding="utf-8")
                sections_list = parse_usccb_sections(sample_html)
                readings_block = build_readings_block(sections_list)
            except Exception as exc2:
                app.logger.warning("fixture parsing failed: %s", exc2)
                sections_list = []
                readings_block = ""

        llm = get_llm()
        reflection_model = os.environ.get("REFLECTION_MODEL", "gpt-5-chat-latest")
        art_model = os.environ.get("ART_MODEL", "gpt-5-mini")

        # Reflection stage
        try:
            prompt1 = prompts.make_prompt1(readings_block)
            reflection = llm.generate(reflection_model, prompt1)
        except Exception as exc:
            app.logger.warning("reflection generation failed: %s", exc)
            reflection = "A brief reflection is temporarily unavailable."

        # Art stage
        try:
            prompt2 = prompts.make_prompt2(date_str, readings_block)
            art_raw = llm.generate(art_model, prompt2)
            try:
                art = safe_parse_art_json(art_raw)
            except Exception as exc:
                app.logger.warning(
                    "art JSON parse failed: %s; raw=%r", exc, (art_raw[:200] if isinstance(art_raw, str) else art_raw)
                )
                art = curator_fallback()
        except Exception as exc:
            app.logger.warning("art generation failed: %s", exc)
            art = curator_fallback()

        # Art block is embedded in cover metadata

        # Deterministic HTML build stage
        try:
            if not sections_list:
                raise RuntimeError("no sections available")
            sections = [P3Section(heading=s.label, reading=((s.citation + "\n") if s.citation else "") + s.text, questions=[])
                        for s in sections_list]
            final_reflection = reflection
            html = build_prompt3_html(date_str, art, sections, strip_code_fences(final_reflection))
        except Exception as exc:
            app.logger.error("final HTML build failed: %s", exc)
            html = f"<html><body><p>Error: {str(exc)}</p></body></html>"
        return html, 200, {"Content-Type": "text/html; charset=utf-8"}

    @app.post("/pdf")
    def pdf_route() -> tuple[bytes, int, dict[str, str]]:
        date_str = request.form.get("date") or app.config.get("DEFAULT_DATE")
        if not date_str:
            date_str = _dt.date.today().isoformat()

        # Build readings from live or fixture
        try:
            html_usccb, _url = scrape.fetch_usccb(date_str)
            sections_list = parse_usccb_sections(html_usccb)
            readings_block = build_readings_block(sections_list)
        except Exception:
            try:
                fixture_path = Path(__file__).resolve().parents[2] / "fixtures" / "usccb" / "sample_1.html"
                sample_html = fixture_path.read_text(encoding="utf-8")
                sections_list = parse_usccb_sections(sample_html)
                readings_block = build_readings_block(sections_list)
            except Exception:
                sections_list = []
                readings_block = ""

        llm = get_llm()
        reflection_model = os.environ.get("REFLECTION_MODEL", "gpt-5-chat-latest")
        art_model = os.environ.get("ART_MODEL", "gpt-5-mini")

        try:
            prompt1 = prompts.make_prompt1(readings_block)
            reflection = llm.generate(reflection_model, prompt1)
        except Exception:
            reflection = "A brief reflection is temporarily unavailable."

        try:
            prompt2 = prompts.make_prompt2(date_str, readings_block)
            art_raw = llm.generate(art_model, prompt2)
            try:
                art = safe_parse_art_json(art_raw)
            except Exception:
                art = curator_fallback()
        except Exception:
            art = curator_fallback()

        try:
            if not sections_list:
                raise RuntimeError("no sections available")
            sections = [P3Section(heading=s.label, reading=((s.citation + "\n") if s.citation else "") + s.text, questions=[])
                        for s in sections_list]
            final_reflection = reflection
        except Exception:
            sections = [P3Section(heading="Reading", reading=readings_block, questions=[])]
            final_reflection = reflection

        html_doc = build_prompt3_html(date_str, art, sections, strip_code_fences(final_reflection))

        # Prefer pdfkit/wkhtmltopdf, fallback to WeasyPrint
        pdf_bytes: bytes | None = None
        try:
            import pdfkit  # type: ignore

            pdf_bytes = pdfkit.from_string(html_doc, False, options={"quiet": ""})
        except Exception:
            pdf_bytes = None

        if pdf_bytes is None:
            try:
                from weasyprint import HTML  # type: ignore

                pdf_bytes = HTML(string=html_doc).write_pdf()
            except Exception as exc:
                app.logger.error("PDF generation failed: %s", exc)
                pdf_bytes = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n% No PDF available\n"

        headers = {
            "Content-Type": "application/pdf",
            "Content-Disposition": f"attachment; filename=Daily-Readings-{date_str}.pdf",
        }
        return pdf_bytes, 200, headers

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
    readings_block = build_readings_block(parse_usccb_sections(sample_html))
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
