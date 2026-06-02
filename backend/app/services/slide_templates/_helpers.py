from __future__ import annotations

from typing import List, Tuple

from app.services.slide_renderers.context import RenderContext
from app.services.slide_content_density import normalize_content_text, short_heading_from_body
from app.services.slide_renderers.drawing import add_subtitle, add_title
from app.services.slide_renderers.layout_bounds import TITLE_ZONE_BOTTOM_PCT, content_bounds_for_slide
from app.services.slide_renderers.content_cell import render_equal_cells_row, render_equal_cells_stack


def render_with_title(ctx: RenderContext) -> None:
    add_title(ctx, top_pct=0.06, height_pct=max(0.12, TITLE_ZONE_BOTTOM_PCT - 0.08))


def _card_pairs(cards: list, *, heading_fn=None) -> List[Tuple[str, str]]:
    pairs: List[Tuple[str, str]] = []
    for index, item in enumerate(cards):
        title = item.title if hasattr(item, "title") else str(item[0])
        text = item.text if hasattr(item, "text") else str(item[1])
        title_norm = normalize_content_text(title)
        text_norm = normalize_content_text(text)
        body = text_norm or title_norm
        if not body:
            continue
        if heading_fn:
            head = heading_fn(index)
        elif text_norm and title_norm and title_norm != text_norm and len(title_norm) <= 50:
            head = title_norm
        else:
            head = short_heading_from_body(body)
        pairs.append((head, body))
    return pairs


def render_cards_text_column(ctx: RenderContext, cards: list, *, heading_fn=None) -> None:
    bounds = content_bounds_for_slide(ctx)
    pairs = _card_pairs(cards, heading_fn=heading_fn)
    if not pairs:
        return
    limit = 2 if ctx.has_image_zone else 4
    render_equal_cells_stack(ctx, bounds, pairs[:limit])


def render_cards_grid(ctx: RenderContext, cards: list, *, heading_fn=None) -> None:
    render_dense_grid(ctx, cards, heading_fn=heading_fn)


def render_cards_featured(ctx: RenderContext, cards: list) -> None:
    from app.services.slide_templates.visual_layouts import render_hero_split

    render_hero_split(ctx, cards)


def render_cards_horizontal(ctx: RenderContext, cards: list) -> None:
    bounds = content_bounds_for_slide(ctx)
    pairs = _card_pairs(cards)
    if not pairs:
        return
    if len(pairs) > 2 or ctx.has_image_zone:
        render_equal_cells_stack(ctx, bounds, pairs[:4])
        return
    items = [(h, b, None) for h, b in pairs[:2]]
    render_equal_cells_row(
        ctx,
        left_pct=bounds.left_pct,
        top_pct=bounds.top_pct,
        width_pct=bounds.right_pct - bounds.left_pct,
        height_pct=bounds.bottom_pct - bounds.top_pct,
        items=items,
    )


def render_stacked_points(
    ctx: RenderContext,
    points: list[str],
    *,
    heading: str = "•",
    max_items: int = 4,
) -> None:
    bounds = content_bounds_for_slide(ctx)
    limit = 2 if ctx.has_image_zone else max_items
    pairs = [(heading, p) for p in points[:limit]]
    render_equal_cells_stack(ctx, bounds, pairs)


def render_sidebar_list(ctx: RenderContext, items: List[Tuple[str, str]]) -> None:
    bounds = content_bounds_for_slide(ctx)
    limit = 2 if ctx.has_image_zone else 4
    render_equal_cells_stack(ctx, bounds, items[:limit])
