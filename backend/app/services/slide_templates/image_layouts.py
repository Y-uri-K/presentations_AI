from __future__ import annotations

"""Макеты слайдов с зоной иллюстрации — контент только в content_bounds."""

from app.services.slide_renderers.context import RenderContext
from app.services.slide_renderers.content_cell import render_equal_cells_stack
from app.services.slide_renderers.layout_bounds import content_bounds_for_slide
from app.services.slide_templates._helpers import render_sidebar_list, render_with_title
from app.services.slide_templates.visual_layouts import render_dense_kpi_row


def render_image_column_cards(ctx: RenderContext, cards: list) -> None:
    render_with_title(ctx)
    pairs = [(c.title, c.text) for c in cards[:4]]
    render_sidebar_list(ctx, pairs)


def render_image_column_texts(ctx: RenderContext, items: list[str], *, prefix: str = "•") -> None:
    render_with_title(ctx)
    pairs: list[tuple[str, str]] = []
    for i, t in enumerate(items[:4]):
        if prefix:
            heading = f"{prefix} {i + 1}".strip()
        else:
            heading = str(i + 1)
        pairs.append((heading, t))
    render_sidebar_list(ctx, pairs)


def render_image_metrics_column(ctx: RenderContext, metrics: list) -> None:
    render_with_title(ctx)
    render_dense_kpi_row(ctx, metrics[:3])


def render_image_comparison_stack(ctx: RenderContext, spec) -> None:
    """Сравнение: контент сверху, иллюстрация снизу (placement=vertical)."""
    render_with_title(ctx)
    bounds = content_bounds_for_slide(ctx)
    left_body = "\n".join(spec.left.points[:5])
    right_body = "\n".join(spec.right.points[:5])
    render_equal_cells_stack(
        ctx,
        bounds,
        [
            (spec.left.heading, left_body),
            (spec.right.heading, right_body),
        ],
        accent_index=1,
        max_items=2,
    )


def render_image_diagram_split(ctx: RenderContext, points: list[str]) -> None:
    render_with_title(ctx)
    render_sidebar_list(ctx, [(f"{i + 1}", p) for i, p in enumerate(points[:4])])
