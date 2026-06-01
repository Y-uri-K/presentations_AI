from __future__ import annotations

from app.schemas.semantic_slides import DiagramSlide
from app.services.slide_renderers.context import RenderContext
from app.services.slide_renderers.drawing import add_subtitle
from app.services.slide_renderers.layout_bounds import content_bounds_for_slide
from app.services.slide_templates._helpers import render_stacked_points, render_with_title
from app.services.slide_templates.image_layouts import render_image_diagram_split


def render_diagram(ctx: RenderContext, variant: str) -> None:
    spec: DiagramSlide = ctx.spec  # type: ignore[assignment]
    points = spec.key_points[:6] or [spec.title]
    if variant == "image_visual_split" or ctx.has_image_zone:
        render_image_diagram_split(ctx, points)
        return

    render_with_title(ctx)
    bounds = content_bounds_for_slide(ctx)
    limit = 3 if ctx.has_image_zone else 4
    render_stacked_points(ctx, points, max_items=limit)

    if spec.caption:
        add_subtitle(ctx, spec.caption, top_pct=min(0.86, bounds.bottom_pct))
