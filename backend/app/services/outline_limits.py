from __future__ import annotations

import re

from fastapi import HTTPException, status

from app.config import get_settings

_SLIDE_HEADING = re.compile(r"^#{1,2}\s+.+", re.MULTILINE)
_HEADING_START = re.compile(r"^#{1,2}\s+", re.MULTILINE)
_TITLE_TAG_RE = re.compile(r"<TITLE>\s*.*?\s*</TITLE>", re.DOTALL | re.IGNORECASE)


def _plan_body(outline: str) -> str:
    """План без <TITLE> — название презентации не считается слайдом."""
    return _TITLE_TAG_RE.sub("", outline).strip()


def count_outline_slides(outline: str) -> int:
    trimmed = _plan_body(outline)
    if not trimmed:
        return 0
    headings = _SLIDE_HEADING.findall(trimmed)
    return len(headings) if headings else 1


def truncate_outline(outline: str, max_slides: int | None = None) -> str:
    limit = max_slides if max_slides is not None else get_settings().presentation_max_slides
    title_match = _TITLE_TAG_RE.search(outline)
    title_prefix = ""
    if title_match:
        title_prefix = title_match.group(0).strip() + "\n\n"
    trimmed = _plan_body(outline)
    if not trimmed:
        return title_prefix.strip()

    matches = list(_HEADING_START.finditer(trimmed))
    if len(matches) <= limit:
        body = trimmed
    elif limit <= 0:
        body = ""
    else:
        body = trimmed[: matches[limit].start()].strip()
    return f"{title_prefix}{body}".strip() if body else title_prefix.strip()


def ensure_outline_within_limit(outline: str) -> str:
    limit = get_settings().presentation_max_slides
    cleaned = outline.strip()
    count = count_outline_slides(cleaned)
    if count > limit:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"В плане {count} слайдов. Максимум — {limit}. Удалите лишние разделы (заголовки ##).",
        )
    return cleaned
