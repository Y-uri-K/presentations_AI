from __future__ import annotations

from app.schemas.semantic_slides import CardsSlide
from app.services.slide_renderers.context import RenderContext
from app.services.slide_templates._helpers import (
    render_cards_featured,
    render_cards_grid,
    render_cards_horizontal,
    render_cards_text_column,
    render_sidebar_list,
    render_with_title,
)
from app.services.slide_templates.image_layouts import render_image_column_cards


def render_cards(ctx: RenderContext, variant: str) -> None:
    spec: CardsSlide = ctx.spec  # type: ignore[assignment]
    cards = spec.cards[:6]
    if variant == "image_column" or ctx.has_image_zone:
        render_image_column_cards(ctx, cards)
        return

    render_with_title(ctx)
    if variant == "featured":
        render_cards_featured(ctx, cards)
    elif variant == "horizontal_strip":
        render_cards_horizontal(ctx, cards)
    elif variant == "sidebar_list":
        render_sidebar_list(ctx, [(c.title, c.text) for c in cards])
    elif variant in ("mosaic", "staggered"):
        render_cards_text_column(ctx, cards)
    else:
        render_cards_grid(ctx, cards)
