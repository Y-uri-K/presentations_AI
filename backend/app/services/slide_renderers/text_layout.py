from __future__ import annotations

"""Оценка высоты текста для раскладки слайда."""

_MARGIN_LEFT_PCT = 0.06
_USABLE_WIDTH_PCT = 0.88
SLIDE_HALF_WIDTH_PCT = _USABLE_WIDTH_PCT / 2
COLUMN_GAP_PCT = 0.02

MIN_CARD_HEIGHT_PCT = 0.10
LINE_HEIGHT_PCT = 0.052
_CARD_PAD_LINES = 2
_HEIGHT_SAFETY = 1.75


def effective_text_width_pct(width_pct: float, *, style: str = "rounded") -> float:
    """Ширина колонки текста с учётом полосы sidebar."""
    if style == "sidebar":
        return width_pct * 0.88
    return width_pct * 0.94


def chars_per_line(width_pct: float, *, font_pt: float = 11) -> int:
    """Консервативная оценка — больше строк, выше фигура."""
    del font_pt
    return max(14, int(width_pct * 68))


def estimate_block_height_pct(
    text: str,
    width_pct: float,
    *,
    extra_lines: int = 0,
) -> float:
    cleaned = (text or "").strip()
    if not cleaned:
        return MIN_CARD_HEIGHT_PCT
    cpl = chars_per_line(width_pct)
    wrapped_lines = sum(max(1, (len(part) + cpl - 1) // cpl) for part in cleaned.split("\n"))
    lines = wrapped_lines + extra_lines + _CARD_PAD_LINES
    return MIN_CARD_HEIGHT_PCT + lines * LINE_HEIGHT_PCT


def card_content_height_pct(
    heading: str,
    body: str,
    width_pct: float,
    *,
    style: str = "rounded",
) -> float:
    text_w = effective_text_width_pct(width_pct, style=style)
    parts: list[str] = []
    head = (heading or "").strip()
    text = (body or "").strip()
    if head and head not in ("—", "-", "•") and head != text:
        parts.append(head)
    parts.append(text or head)
    return estimate_block_height_pct("\n".join(parts), text_w) * _HEIGHT_SAFETY


def estimate_pair_height_pct(heading: str, body: str, width_pct: float) -> float:
    return card_content_height_pct(heading, body, width_pct)
