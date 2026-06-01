from __future__ import annotations

from typing import List, Tuple

from app.services.slide_renderers.context import RenderContext
from app.services.slide_content_density import normalize_content_text, short_heading_from_body
from app.services.slide_renderers.drawing import add_card, add_card_stack, add_subtitle, add_title
from app.services.slide_renderers.layout_bounds import TITLE_ZONE_BOTTOM_PCT, content_bounds_for_slide


def render_with_title(ctx: RenderContext) -> None:
    add_title(ctx, top_pct=0.06, height_pct=max(0.12, TITLE_ZONE_BOTTOM_PCT - 0.08))


def card_items_from_pairs(pairs: List[Tuple[str, str]]):
    return pairs


def _card_pairs(cards: list, *, heading_fn=None) -> List[Tuple[str, str]]:
    pairs: List[Tuple[str, str]] = []
    for index, item in enumerate(cards):
        title = item.title if hasattr(item, "title") else str(item[0])
        text = item.text if hasattr(item, "text") else str(item[1])
        body = normalize_content_text(text) or normalize_content_text(title)
        if not body:
            continue
        head = heading_fn(index) if heading_fn else normalize_content_text(title)
        if not head or head == body or len(head) > 50:
            head = short_heading_from_body(body)
        pairs.append((head, body))
    return pairs


def render_cards_text_column(ctx: RenderContext, cards: list, *, heading_fn=None) -> None:
    """Список карточек фигурами с автовысотой и переносом строк."""
    bounds = content_bounds_for_slide(ctx)
    pairs = _card_pairs(cards, heading_fn=heading_fn)
    if not pairs:
        return
    limit = 2 if ctx.has_image_zone else 3
    add_card_stack(
        ctx,
        left_pct=bounds.left_pct,
        top_pct=bounds.top_pct,
        width_pct=bounds.right_pct - bounds.left_pct,
        bottom_pct=bounds.bottom_pct,
        items=pairs[:limit],
    )


def render_cards_grid(ctx: RenderContext, cards: list, *, heading_fn=None) -> None:
    render_cards_text_column(ctx, cards, heading_fn=heading_fn)


def render_cards_featured(ctx: RenderContext, cards: list) -> None:
    render_cards_text_column(ctx, cards)


def render_cards_horizontal(ctx: RenderContext, cards: list) -> None:
    if len(cards) > 2 or ctx.has_image_zone:
        render_cards_text_column(ctx, cards)
        return
    bounds = content_bounds_for_slide(ctx)
    count = min(len(cards), 2)
    gap = 0.02
    w = (bounds.right_pct - bounds.left_pct - gap * (count - 1)) / count
    h = bounds.bottom_pct - bounds.top_pct
    for index, item in enumerate(cards[:count]):
        add_card(
            ctx,
            left_pct=bounds.left_pct + index * (w + gap),
            top_pct=bounds.top_pct,
            width_pct=w,
            height_pct=h,
            heading=item.title if hasattr(item, "title") else str(item[0]),
            body=item.text if hasattr(item, "text") else str(item[1]),
            accent=index == 0,
            style="rectangle",
        )


_MIN_STACK_CARD_HEIGHT_PCT = 0.12
_MAX_SIDEBAR_ITEMS = 3
_MAX_SIDEBAR_ITEMS_NARROW = 2


def _sidebar_item_limit(ctx: RenderContext, bounds) -> int:
    width = bounds.right_pct - bounds.left_pct
    if ctx.has_image_zone or width < 0.55:
        return _MAX_SIDEBAR_ITEMS_NARROW
    return _MAX_SIDEBAR_ITEMS


def render_stacked_points(
    ctx: RenderContext,
    points: list[str],
    *,
    heading: str = "•",
    max_items: int = 4,
) -> None:
    """Вертикальный список с достаточной высотой строк."""
    limit = 2 if ctx.has_image_zone else max_items
    pairs = [(heading, p) for p in points[:limit]]
    render_sidebar_list(ctx, pairs)


def render_sidebar_list(ctx: RenderContext, items: List[Tuple[str, str]]) -> None:
    bounds = content_bounds_for_slide(ctx)
    width_span = bounds.right_pct - bounds.left_pct
    limit = _sidebar_item_limit(ctx, bounds)
    add_card_stack(
        ctx,
        left_pct=bounds.left_pct,
        top_pct=bounds.top_pct,
        width_pct=width_span,
        bottom_pct=bounds.bottom_pct,
        items=items[:limit],
        style="sidebar",
    )
