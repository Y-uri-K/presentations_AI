from __future__ import annotations

from app.schemas.semantic_slides import CardsSlide
from app.services.slide_renderers.context import RenderContext
from app.services.slide_templates._helpers import (
    _card_pairs,
    render_cards_horizontal,
    render_with_title,
)
from app.services.slide_renderers.content_cell import render_equal_cells_stack
from app.services.slide_renderers.layout_bounds import content_bounds_for_slide
from app.services.slide_templates.image_layouts import render_image_column_cards
from app.services.slide_templates.visual_layouts import render_dense_grid, render_hero_split


def render_cards(ctx: RenderContext, variant: str) -> None:
    spec: CardsSlide = ctx.spec  # type: ignore[assignment]
    cards = spec.cards[:6]
    if variant == "image_column" or ctx.has_image_zone:
        render_image_column_cards(ctx, cards)
        return

    render_with_title(ctx)
    if variant == "hero_featured":
        render_hero_split(ctx, cards)
    elif variant == "horizontal_strip":
        render_cards_horizontal(ctx, cards)
    elif variant == "sidebar_list":
        bounds = content_bounds_for_slide(ctx)
        render_equal_cells_stack(ctx, bounds, _card_pairs(cards)[:4])
    else:
        render_dense_grid(ctx, cards)
