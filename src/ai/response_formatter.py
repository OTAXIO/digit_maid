from __future__ import annotations

import html
import json
import re

try:
    import markdown as markdown_lib
except Exception:
    markdown_lib = None


_UNSAFE_TAG_PATTERN = re.compile(r"<\s*/?\s*(script|style|iframe|object|embed)[^>]*>", re.IGNORECASE)
_CONTROL_CHAR_PATTERN = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")
_MARKDOWN_HINT_PATTERN = re.compile(
    r"(^#{1,6}\s)|(^[-*+]\s)|(^\d+\.\s)|(```)|(`[^`]+`)|(\[[^\]]+\]\([^\)]+\))|(\*\*[^*]+\*\*)",
    re.MULTILINE,
)


def format_response_content(raw_text: str) -> dict[str, str]:
    cleaned = _clean_text(raw_text)

    if _looks_like_json(cleaned):
        try:
            parsed = json.loads(cleaned)
            pretty = json.dumps(parsed, ensure_ascii=False, indent=2)
            return {
                "render_type": "json",
                "text": pretty,
                "html": _wrap_pre(pretty),
            }
        except json.JSONDecodeError:
            pass

    if markdown_lib is not None and _looks_like_markdown(cleaned):
        escaped = html.escape(cleaned, quote=False)
        rendered = markdown_lib.markdown(
            escaped,
            extensions=["extra", "nl2br", "sane_lists"],
            output_format="html5",
        )
        return {
            "render_type": "markdown",
            "text": cleaned,
            "html": rendered,
        }

    return {
        "render_type": "text",
        "text": cleaned,
        "html": _wrap_pre(cleaned),
    }


def _clean_text(value: str) -> str:
    text = str(value or "")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _UNSAFE_TAG_PATTERN.sub("", text)
    text = _CONTROL_CHAR_PATTERN.sub("", text)
    return text.strip()


def _looks_like_json(text: str) -> bool:
    if not text:
        return False
    return text.startswith("{") or text.startswith("[")


def _looks_like_markdown(text: str) -> bool:
    if not text:
        return False
    return bool(_MARKDOWN_HINT_PATTERN.search(text))


def _wrap_pre(text: str) -> str:
    escaped = html.escape(text, quote=False)
    return (
        "<pre style='white-space: pre-wrap; word-break: break-word; margin: 0; "
        "font-family: Consolas, Microsoft YaHei, monospace;'>"
        f"{escaped}</pre>"
    )
