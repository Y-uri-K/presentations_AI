from __future__ import annotations

from app.schemas.semantic_slides import DiagramSlide
from app.services.slide_renderers.context import RenderContext
from app.services.slide_renderers.drawing import add_subtitle
from app.services.slide_renderers.layout_bounds import content_bounds_for_slide
from app.services.slide_templates._helpers import render_with_title
from app.services.slide_templates.image_layouts import render_image_diagram_split
from app.services.slide_templates.visual_layouts import render_dense_grid, render_two_columns


def render_diagram(ctx: RenderContext, variant: str) -> None:
    spec: DiagramSlide = ctx.spec  # type: ignore[assignment]
    points = spec.key_points[:6] or [spec.title]
    if variant == "image_visual_split" or ctx.has_image_zone:
        render_image_diagram_split(ctx, points)
        return

    render_with_title(ctx)
    bounds = content_bounds_for_slide(ctx)

    if variant in ("two_column", "stacked", "callout_lead", "pyramid"):
        render_two_columns(ctx, points)
    else:
        items = [type("C", (), {"title": str(i + 1), "text": p})() for i, p in enumerate(points[:4])]
        render_dense_grid(ctx, items)

    if spec.caption:
        add_subtitle(ctx, spec.caption, top_pct=min(0.86, bounds.bottom_pct))
