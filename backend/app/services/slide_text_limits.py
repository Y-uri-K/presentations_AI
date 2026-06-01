from __future__ import annotations

"""Лимиты длины текста слайдов (не ИИ-агент — постобработка при сборке)."""

MAX_TITLE_CHARS = 150
MAX_BODY_CHARS = 2000
MAX_CARD_TITLE_CHARS = 100
MAX_SUBTITLE_CHARS = 800


def card_title_from_text(text: str, *, index: int = 1) -> str:
    """Короткий заголовок карточки; полный текст остаётся в body."""
    from app.services.slide_content_density import short_heading_from_body

    line = (text or "").strip().split("\n")[0].strip()
    if not line:
        return f"Пункт {index}"
    return short_heading_from_body(line, max_words=8)


def clamp_text(value: str, limit: int, *, ellipsis: bool = True) -> str:
    cleaned = " ".join((value or "").split())
    if len(cleaned) <= limit:
        return cleaned
    if ellipsis:
        return cleaned[: limit - 1].rstrip() + "…"
    return cleaned[:limit]
