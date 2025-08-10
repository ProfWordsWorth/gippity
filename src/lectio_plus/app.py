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
from .parse import (
    parse_usccb_html as parse_usccb_sections,
    make_prompt3_sections,
    build_readings_block,
    sections_to_text,
    safe_parse_sections_json,
)
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
            "<!DOCTYPE html><html><head><meta charset='utf-8'>"
            "<meta name='viewport' content='width=device-width, initial-scale=1'>"
            "<title>Lectio+ Daily Readings</title>"
            "<style>body{font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;margin:20px;color:#222}"
            ".wrap{max-width:720px;margin:0 auto}h1{margin:0 0 12px}p.hint{color:#555}form{display:inline-block;margin:4px 6px 0 0}"
            "input[type=date]{padding:6px 8px;border:1px solid #ccc;border-radius:4px}button{padding:6px 10px;border:1px solid #0a7;border-radius:4px;background:#0a7;color:#fff;cursor:pointer}button.secondary{background:#555;border-color:#555}"
            "#overlay{position:fixed;inset:0;background:rgba(255,255,255,0.8);display:none;align-items:center;justify-content:center;font-size:16px;color:#333}"
            "</style></head><body><div class='wrap'>"
            "<h1>Lectio+ Daily Readings</h1>"
            "<p class='hint'>Generate a printable reflection booklet for the selected date. </p>"
            "<div>"
            "<form method='post' action='/run'>"
            f"<input type='date' name='date' value='{value}'> "
            "<button type='submit'>Generate</button>"
            "</form>"
            "<form method='post' action='/pdf'>"
            f"<input type='hidden' name='date' value='{value}'>"
            " <button class='secondary' type='submit'>Download PDF</button>"
            "</form>"
            "</div>"
            "</div><div id='overlay'>Working… Please wait.</div>"
            "<script>for(const f of document.querySelectorAll('form')){f.addEventListener('submit',()=>{document.getElementById('overlay').style.display='flex';});}</script>"
            "</body></html>"
        )

    @app.post("/run")
    def run_route() -> tuple[str, int, dict[str, str]]:
        date_str = request.form.get("date") or app.config.get("DEFAULT_DATE")
        if not date_str:
            date_str = _dt.date.today().isoformat()

        sections_list: list | None = None
        readings_source_url: str | None = None
        try:
            html_usccb, _url = scrape.fetch_usccb(date_str)
            sections_list = parse_usccb_sections(html_usccb)
            readings_block = build_readings_block(sections_list)
            readings_source_url = _url
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

        # Optional: enrich sections with context/exegesis/questions via LLM
        enriched_sections: list[P3Section] | None = None
        if os.getenv("ENABLE_ENRICH_SECTIONS") == "1":
            try:
                sections_text = sections_to_text(sections_list)
                prompt_sections = prompts.make_prompt_sections(date_str, sections_text)
                sections_model = os.environ.get("SECTIONS_MODEL", reflection_model)
                enrichment_raw = llm.generate(sections_model, prompt_sections)
                enrichment = safe_parse_sections_json(enrichment_raw)
                items = enrichment.get("sections") or []
                final_ref = enrichment.get("final_reflection")
                enriched_sections = []
                for idx, s in enumerate(sections_list):
                    item = items[idx] if idx < len(items) else {}
                    context = item.get("context") if isinstance(item, dict) else None
                    exegesis = item.get("exegesis") if isinstance(item, dict) else None
                    questions = item.get("questions") if isinstance(item, dict) else []
                    if not isinstance(questions, list):
                        questions = []
                    enriched_sections.append(
                        P3Section(
                            heading=s.label,
                            reading=((s.citation + "\n") if s.citation else "") + s.text,
                            context=context or None,
                            exegesis=exegesis or None,
                            questions=[str(q) for q in questions][:4],
                        )
                    )
                if isinstance(final_ref, str) and final_ref.strip():
                    reflection = final_ref.strip()
            except Exception as exc:
                app.logger.warning("section enrichment failed: %s", exc)

        # Deterministic HTML build stage
        try:
            if not sections_list:
                raise RuntimeError("no sections available")
            if enriched_sections is None:
                sections = [P3Section(heading=s.label, reading=((s.citation + "\n") if s.citation else "") + s.text, questions=[])
                            for s in sections_list]
            else:
                sections = enriched_sections
            final_reflection = reflection
            html = build_prompt3_html(
                date_str,
                art,
                sections,
                strip_code_fences(final_reflection),
                source_url=readings_source_url,
            )
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
        readings_source_url: str | None = None
        try:
            html_usccb, _url = scrape.fetch_usccb(date_str)
            sections_list = parse_usccb_sections(html_usccb)
            readings_block = build_readings_block(sections_list)
            readings_source_url = _url
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

        # Optional enrichment for sections
        enriched_sections: list[P3Section] | None = None
        if os.getenv("ENABLE_ENRICH_SECTIONS") == "1":
            try:
                sections_text = sections_to_text(sections_list)
                prompt_sections = prompts.make_prompt_sections(date_str, sections_text)
                sections_model = os.environ.get("SECTIONS_MODEL", reflection_model)
                enrichment_raw = llm.generate(sections_model, prompt_sections)
                enrichment = safe_parse_sections_json(enrichment_raw)
                items = enrichment.get("sections") or []
                final_ref = enrichment.get("final_reflection")
                enriched_sections = []
                for idx, s in enumerate(sections_list):
                    item = items[idx] if idx < len(items) else {}
                    context = item.get("context") if isinstance(item, dict) else None
                    exegesis = item.get("exegesis") if isinstance(item, dict) else None
                    questions = item.get("questions") if isinstance(item, dict) else []
                    if not isinstance(questions, list):
                        questions = []
                    enriched_sections.append(
                        P3Section(
                            heading=s.label,
                            reading=((s.citation + "\n") if s.citation else "") + s.text,
                            context=context or None,
                            exegesis=exegesis or None,
                            questions=[str(q) for q in questions][:4],
                        )
                    )
                if isinstance(final_ref, str) and final_ref.strip():
                    reflection = final_ref.strip()
            except Exception as exc:
                app.logger.warning("section enrichment failed: %s", exc)

        try:
            if not sections_list:
                raise RuntimeError("no sections available")
            if enriched_sections is None:
                sections = [P3Section(heading=s.label, reading=((s.citation + "\n") if s.citation else "") + s.text, questions=[])
                            for s in sections_list]
            else:
                sections = enriched_sections
            final_reflection = reflection
        except Exception:
            sections = [P3Section(heading="Reading", reading=readings_block, questions=[])]
            final_reflection = reflection

        html_doc = build_prompt3_html(
            date_str,
            art,
            sections,
            strip_code_fences(final_reflection),
            source_url=readings_source_url,
        )

        # Prefer pdfkit/wkhtmltopdf, fallback to WeasyPrint, then reportlab
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
                app.logger.warning("WeasyPrint failed: %s; using reportlab fallback", exc)
                try:
                    # Last resort: valid single-page PDF with plain text
                    from reportlab.lib.pagesizes import letter  # type: ignore
                    from reportlab.pdfgen import canvas  # type: ignore
                    import io

                    buf = io.BytesIO()
                    c = canvas.Canvas(buf, pagesize=letter)
                    width, height = letter
                    c.setFont("Helvetica", 14)
                    c.drawString(72, height - 72, f"Daily Readings — {date_str}")
                    c.setFont("Helvetica", 10)
                    y = height - 96
                    c.drawString(72, y, "Open the HTML version for full layout and images.")
                    y -= 18
                    if isinstance(art, dict) and art.get("title"):
                        c.drawString(72, y, f"Artwork: {art.get('title')} by {art.get('artist')} ({art.get('year')})")
                        y -= 18
                    if isinstance(readings_source_url, str) and readings_source_url:
                        c.drawString(72, y, f"Source: {readings_source_url}")
                    c.showPage()
                    c.save()
                    pdf_bytes = buf.getvalue()
                except Exception as exc2:
                    app.logger.error("Reportlab fallback failed: %s", exc2)
                    pdf_bytes = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n2 0 obj<</Type/Pages/Count 0/Kids[]>>endobj\ntrailer<</Root 1 0 R>>\n%%EOF\n"

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
