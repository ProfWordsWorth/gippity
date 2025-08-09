"""Application entry points and LLM provider selection for :mod:`lectio_plus`."""

from __future__ import annotations

import os
from typing import Protocol

from . import prompts
from .curator import curate, parse_art_json
from .html_build import build_html


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

        client = OpenAI(
            base_url=self._base_url,
            api_key=self._api_key,
            timeout=10.0,
        )
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


def run(readings_block: str) -> str:
    """Generate HTML for ``readings_block`` using the configured LLM provider."""

    llm = get_llm()
    reflection_model = os.environ.get("REFLECTION_MODEL", "gpt-5-chat-latest")
    art_model = os.environ.get("ART_MODEL", "gpt-5-mini")
    html_model = os.environ.get("HTML_MODEL", "gpt-5-mini")

    prompt1 = prompts.make_prompt1(readings_block)
    reflection = llm.generate(reflection_model, prompt1)

    prompt2 = prompts.make_prompt2("DATE", readings_block)
    art_raw = llm.generate(art_model, prompt2)
    art = parse_art_json(art_raw)
    art_block = curate([art["title"], art["artist"], art["year"], art["image_url"]])

    raw_blocks = curate([reflection, art_block])
    prompt3 = prompts.make_prompt3("DATE", raw_blocks)
    injected_html = llm.generate(html_model, prompt3)
    return build_html(injected_html)


__all__ = ["LLM", "FakeLLM", "OpenAILLM", "get_llm", "run"]
