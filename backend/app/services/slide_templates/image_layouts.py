from __future__ import annotations

"""Макеты слайдов с зоной иллюстрации — контент только в content_bounds."""

from app.services.slide_renderers.context import RenderContext
from app.services.slide_renderers.drawing import add_card, add_card_stack
from app.services.slide_renderers.layout_bounds import content_bounds_for_slide
from app.services.slide_templates._helpers import render_sidebar_list, render_with_title


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
    bounds = content_bounds_for_slide(ctx)
    pairs = [
        (metric.value, f"{metric.label}\n{metric.note or ''}".strip())
        for metric in metrics[:3]
    ]
    add_card_stack(
        ctx,
        left_pct=bounds.left_pct,
        top_pct=bounds.top_pct,
        width_pct=bounds.right_pct - bounds.left_pct,
        bottom_pct=bounds.bottom_pct,
        items=pairs,
        style="flat",
    )


def render_image_comparison_stack(ctx: RenderContext, spec) -> None:
    """Сравнение: контент сверху, иллюстрация снизу (placement=vertical)."""
    render_with_title(ctx)
    bounds = content_bounds_for_slide(ctx)
    left_body = "\n\n".join(spec.left.points[:3])
    right_body = "\n\n".join(spec.right.points[:3])
    add_card_stack(
        ctx,
        left_pct=bounds.left_pct,
        top_pct=bounds.top_pct,
        width_pct=bounds.right_pct - bounds.left_pct,
        bottom_pct=bounds.bottom_pct,
        items=[
            (spec.left.heading, left_body),
            (spec.right.heading, right_body),
        ],
        accent_first=False,
        style="flat",
    )


def render_image_diagram_split(ctx: RenderContext, points: list[str]) -> None:
    from app.services.slide_templates._helpers import render_sidebar_list

    render_with_title(ctx)
    render_sidebar_list(ctx, [(f"{i + 1}", p) for i, p in enumerate(points[:3])])
