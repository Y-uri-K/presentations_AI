from __future__ import annotations

"""Оценка высоты текста для раскладки слайда."""

_MARGIN_LEFT_PCT = 0.06
_USABLE_WIDTH_PCT = 0.88
SLIDE_HALF_WIDTH_PCT = _USABLE_WIDTH_PCT / 2  # 0.44 — половина слайда под картинку/текст
COLUMN_GAP_PCT = 0.02

MIN_CARD_HEIGHT_PCT = 0.10
LINE_HEIGHT_PCT = 0.042
_CARD_PAD_LINES = 1


def chars_per_line(width_pct: float, *, font_pt: float = 11) -> int:
    """Грубая оценка символов в строке для кириллицы (с запасом под перенос)."""
    del font_pt
    return max(18, int(width_pct * 82))


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
    lines = max(1, (len(cleaned) + cpl - 1) // cpl) + extra_lines + _CARD_PAD_LINES
    return min(0.48, MIN_CARD_HEIGHT_PCT + lines * LINE_HEIGHT_PCT)


def card_content_height_pct(heading: str, body: str, width_pct: float) -> float:
    parts: list[str] = []
    head = (heading or "").strip()
    text = (body or "").strip()
    if head and head not in ("—", "-", "•") and head != text:
        parts.append(head)
    parts.append(text or head)
    return estimate_block_height_pct("\n".join(parts), width_pct)


def estimate_pair_height_pct(heading: str, body: str, width_pct: float) -> float:
    h = (heading or "").strip()
    b = (body or "").strip()
    if h and h not in ("•", "—") and b and h != b:
        return estimate_block_height_pct(f"{h}\n{b}", width_pct, extra_lines=0)
    return estimate_block_height_pct(b or h, width_pct)
