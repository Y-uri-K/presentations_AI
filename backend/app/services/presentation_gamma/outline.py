from __future__ import annotations

import re
from datetime import datetime
from typing import List, Optional, Tuple

from app.config import get_settings
from app.services.outline_limits import count_outline_slides, truncate_outline
from app.services.presentation_gamma.prompts import outline_system_prompt

_TITLE_RE = re.compile(r"<TITLE>\s*(.*?)\s*</TITLE>", re.DOTALL | re.IGNORECASE)
_TOPIC_RE = re.compile(r"^#{1,2}\s+(.+)$", re.MULTILINE)


def extract_presentation_title(raw: str, fallback: str = "Презентация") -> str:
    match = _TITLE_RE.search(raw)
    if match and match.group(1).strip():
        return match.group(1).strip()[:255]
    for line in raw.splitlines():
        topic = _TOPIC_RE.match(line.strip())
        if topic:
            return topic.group(1).strip()[:255]
    return fallback[:255]


def strip_title_tag(raw: str) -> str:
    cleaned = _TITLE_RE.sub("", raw).strip()
    return cleaned


def parse_outline_chunks(outline_md: str) -> List[str]:
    """Как presentation-ai: массив '# тема\\n- пункт'."""
    trimmed = strip_title_tag(outline_md).strip()
    if not trimmed:
        return []

    parts = re.split(r"(?=\n#{1,2}\s)", "\n" + trimmed)
    chunks: List[str] = []
    for part in parts:
        block = part.strip()
        if not block:
            continue
        if not block.startswith("#"):
            block = f"# {block}"
        chunks.append(block)
    return chunks[: get_settings().presentation_max_slides]


def format_outline_prompt(
    *,
    text_content: str,
    tone: str,
    audience: str,
    scenario: str,
) -> str:
    current_date = datetime.now().strftime("%d %B %Y")
    return (
        outline_system_prompt()
        .replace("{current_date}", current_date)
        .replace("{text_content}", text_content)
        .replace("{tone}", tone)
        .replace("{audience}", audience)
        .replace("{scenario}", scenario)
    )


def normalize_stored_outline(raw: str, *, fallback_title: str) -> Tuple[str, str]:
    """TITLE + markdown, обрезка до лимита слайдов."""
    title = extract_presentation_title(raw, fallback=fallback_title)
    body = strip_title_tag(raw)
    body = truncate_outline(body)
    if count_outline_slides(body) == 0 and body:
        lines = [ln.strip() for ln in body.splitlines() if ln.strip()]
        bullets = "\n".join(
            line if line.startswith("-") else f"- {line}" for line in lines[:8]
        )
        body = f"# Тема 1\n{bullets or '- Содержание слайда'}"
    stored = f"<TITLE>{title}</TITLE>\n\n{body}".strip()
    return title, stored
