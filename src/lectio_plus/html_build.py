"""HTML building helpers and deterministic Prompt-3 layout builder."""

from __future__ import annotations

from dataclasses import dataclass
import html
import re


@dataclass
class Section:
    """Prompt-3 logical section for the booklet layout."""

    heading: str
    reading: str
    context: str | None = None
    exegesis: str | None = None
    questions: list[str] | None = None


def strip_code_fences(text: str) -> str:
    """Remove code fences and common wrappers from model output.

    Strips leading and trailing triple backticks and any language info, as well
    as leading phrases like "Here is" / "Here are" that sometimes wrap content.
    """

    if not text:
        return ""

    s = text.strip()
    # Remove leading ```lang and trailing ``` fences
    if s.startswith("```"):
        s = re.sub(r"^```\w*\n?", "", s)
        s = s.rsplit("```", 1)[0].strip()

    # Drop leading "Here is/are ...:" veneer
    s = re.sub(r"^(here\s+(is|are)[^:]*:\s*)", "", s, flags=re.I)
    # Remove any stray fenced blocks inside
    s = s.replace("```", "")
    return s.strip()


def build_html(body: str) -> str:
    """Wrap ``body`` in a minimal HTML page."""
    return f"<html><body>{body}</body></html>"


def build_prompt3_html(
    date_str: str,
    art: dict,
    sections: list[Section],
    final_reflection: str,
) -> str:
    """Return a complete HTML document for the Prompt‑3 booklet layout.

    The markup is deterministic and does not depend on LLM‑provided HTML.
    """

    # Base template with placeholders; fill with escaped values below
    style = """
<!DOCTYPE html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\">
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
  <title>Daily Readings – {DATE}</title>
  <style>
    body { font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif; margin: 0; padding: 0; color: #222; }
    .page { padding: 24px; max-width: 760px; margin: 0 auto; }
    .cover { text-align: center; margin-bottom: 24px; }
    .cover h1 { margin: 0 0 4px; font-size: 28px; }
    .cover h2 { margin: 0 0 16px; font-weight: 500; font-size: 20px; color: #555; }
    .figurewrap { margin: 0 auto 8px; }
    .figurewrap img { max-width: 100%; height: auto; border-radius: 4px; }
    .caption { font-size: 12px; color: #555; margin-top: 4px; }
    main.content { margin-top: 12px; }
    h2 { font-size: 20px; margin: 20px 0 8px; }
    p { line-height: 1.45; }
    p.context { color: #333; font-size: 14px; }
    .reading { white-space: pre-wrap; background: #fafafa; border: 1px solid #eee; padding: 8px 10px; border-radius: 4px; }
    p.exegesis { font-size: 14px; color: #333; }
    ul.q-list { margin: 6px 0 14px 20px; }
    ul.q-list li { margin: 4px 0; }
    hr { border: 0; border-top: 1px solid #ddd; margin: 18px 0; }
    section.final-reflect { margin-top: 20px; }
  </style>
</head>
<body>
  <div class=\"page\">
    <section class=\"cover\">
      <h1>Daily Readings</h1>
      <h2>{DATE}</h2>
      <div class=\"figurewrap\">
        <img src=\"{IMG}\" alt=\"Artwork\">
      </div>
      <div class=\"caption\">{TITLE}<br>by {ARTIST}, {YEAR}</div>
    </section>
    <main class=\"content\">
"""

    style = (
        style.replace("{DATE}", html.escape(date_str))
        .replace("{IMG}", html.escape(art.get("image_url", "")))
        .replace("{TITLE}", html.escape(art.get("title", "")))
        .replace("{ARTIST}", html.escape(art.get("artist", "")))
        .replace("{YEAR}", html.escape(art.get("year", "")))
    )

    parts: list[str] = [style.lstrip()]

    def needs_rule(h: str) -> bool:
        key = h.lower()
        return (
            key.startswith("responsorial psalm")
            or key.startswith("sequence")
            or key.startswith("gospel")
        )

    for i, sec in enumerate(sections):
        if i > 0 and needs_rule(sec.heading):
            parts.append("      <hr>")
        parts.append(f"      <h2>{html.escape(sec.heading)}</h2>")
        if sec.context:
            parts.append(
                f"      <p class='context'><strong>Context:</strong> {html.escape(strip_code_fences(sec.context))}</p>"
            )
        parts.append(
            f"      <div class='reading'>{html.escape(strip_code_fences(sec.reading))}</div>"
        )
        if sec.exegesis:
            parts.append(
                f"      <p class='exegesis'><strong>Exegetical&nbsp;Note:</strong> {html.escape(strip_code_fences(sec.exegesis))}</p>"
            )
        parts.append("      <p><strong>Reflection&nbsp;Questions:</strong></p>")
        q_list = sec.questions or []
        parts.append("      <ul class='q-list'>")
        for q in q_list:
            parts.append(f"        <li>{html.escape(strip_code_fences(q))}</li>")
        parts.append("      </ul>")

    # Final reflection
    parts.append("      <hr>")
    parts.append("      <section class='final-reflect'>")
    parts.append("        <h2>Final Reflection</h2>")
    parts.append(f"        <div class='reading'>{html.escape(strip_code_fences(final_reflection))}</div>")
    parts.append("      </section>")

    parts.append(
        """
    </main>
  </div>
</body>
</html>
"""
    )

    return "\n".join(parts)


__all__ = ["build_html", "build_prompt3_html", "strip_code_fences", "Section"]
