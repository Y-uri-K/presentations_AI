from __future__ import annotations

"""Плотные макеты: ячейки заполняют всю контентную зону слайда."""

from typing import List, Sequence

from app.schemas.semantic_slides import MetricItem
from app.services.slide_renderers.context import RenderContext
from app.services.slide_renderers.content_cell import (
    render_content_cell,
    render_equal_cells_grid,
    render_equal_cells_row,
    render_equal_cells_stack,
)
from app.services.slide_renderers.layout_bounds import ContentBounds, content_bounds_for_slide
from app.services.slide_templates._helpers import _card_pairs


def render_dense_grid(ctx: RenderContext, cards: list, *, heading_fn=None) -> None:
    bounds = content_bounds_for_slide(ctx)
    pairs = _card_pairs(cards, heading_fn=heading_fn)
    limit = 4 if not ctx.has_image_zone else 2
    render_equal_cells_grid(ctx, bounds, pairs[:limit])


def render_dense_kpi_row(ctx: RenderContext, metrics: Sequence[MetricItem]) -> None:
    bounds = content_bounds_for_slide(ctx)
    items = [
        (
            metric.label,
            (metric.note or "").strip() or metric.label,
            metric.value,
        )
        for metric in metrics[:4]
    ]
    render_equal_cells_row(
        ctx,
        left_pct=bounds.left_pct,
        top_pct=bounds.top_pct,
        width_pct=bounds.right_pct - bounds.left_pct,
        height_pct=bounds.bottom_pct - bounds.top_pct,
        items=items,
    )


def render_dense_kpi_grid(ctx: RenderContext, metrics: Sequence[MetricItem]) -> None:
    bounds = content_bounds_for_slide(ctx)
    visible = list(metrics[:4])
    if not visible:
        return
    count = len(visible)
    cols = 2 if count > 1 and not ctx.has_image_zone else 1
    rows = (count + cols - 1) // cols
    gap = 0.014
    span_w = bounds.right_pct - bounds.left_pct
    span_h = bounds.bottom_pct - bounds.top_pct
    cell_w = (span_w - gap * (cols - 1)) / cols
    cell_h = (span_h - gap * (rows - 1)) / rows

    for index, metric in enumerate(visible):
        row = index // cols
        col = index % cols
        render_content_cell(
            ctx,
            left_pct=bounds.left_pct + col * (cell_w + gap),
            top_pct=bounds.top_pct + row * (cell_h + gap),
            width_pct=cell_w,
            height_pct=cell_h,
            heading=metric.label,
            body=(metric.note or "").strip(),
            kpi_value=metric.value,
            accent=index == 0,
            rounded=True,
        )


def render_hero_split(ctx: RenderContext, cards: list) -> None:
    bounds = content_bounds_for_slide(ctx)
    pairs = _card_pairs(cards)
    if not pairs:
        return
    if ctx.has_image_zone or len(pairs) <= 2:
        render_equal_cells_stack(ctx, bounds, pairs, max_items=2)
        return
    gap = 0.016
    hero_w = 0.58
    col_w = 1.0 - hero_w - gap
    span_h = bounds.bottom_pct - bounds.top_pct
    span_w = bounds.right_pct - bounds.left_pct

    head, body = pairs[0]
    render_content_cell(
        ctx,
        left_pct=bounds.left_pct,
        top_pct=bounds.top_pct,
        width_pct=span_w * hero_w,
        height_pct=span_h,
        heading=head,
        body=body,
        accent=True,
    )
    right_items = pairs[1:4]
    if right_items:
        stack_gap = 0.012
        cell_h = (span_h - stack_gap * (len(right_items) - 1)) / len(right_items)
        for index, (h, b) in enumerate(right_items):
            render_content_cell(
                ctx,
                left_pct=bounds.left_pct + span_w * (hero_w + gap),
                top_pct=bounds.top_pct + index * (cell_h + stack_gap),
                width_pct=span_w * col_w,
                height_pct=cell_h,
                heading=h,
                body=b,
            )


def render_two_columns(ctx: RenderContext, points: Sequence[str]) -> None:
    bounds = content_bounds_for_slide(ctx)
    mid = (bounds.left_pct + bounds.right_pct) / 2
    gap = 0.016
    col_w = mid - bounds.left_pct - gap / 2
    half = (len(points) + 1) // 2
    left = [(f"{i + 1}", p) for i, p in enumerate(points[:half])]
    right = [(f"{i + half + 1}", p) for i, p in enumerate(points[half:6])]
    sub_left = ContentBounds(
        left_pct=bounds.left_pct,
        right_pct=bounds.left_pct + col_w,
        top_pct=bounds.top_pct,
        bottom_pct=bounds.bottom_pct,
    )
    sub_right = ContentBounds(
        left_pct=mid + gap / 2,
        right_pct=bounds.right_pct,
        top_pct=bounds.top_pct,
        bottom_pct=bounds.bottom_pct,
    )
    if left:
        render_equal_cells_stack(ctx, sub_left, left, max_items=3)
    if right:
        render_equal_cells_stack(ctx, sub_right, right, max_items=3, accent_index=0)


def render_visual_conclusion(ctx: RenderContext, takeaways: List[str]) -> None:
    bounds = content_bounds_for_slide(ctx)
    pairs = [(f"Итог {i + 1}", t) for i, t in enumerate(takeaways[:4])]
    render_equal_cells_stack(ctx, bounds, pairs, accent_index=0)


def render_visual_agenda(ctx: RenderContext, items: List[str]) -> None:
    bounds = content_bounds_for_slide(ctx)
    pairs = [(str(i + 1), item) for i, item in enumerate(items[:5])]
    render_equal_cells_stack(ctx, bounds, pairs)


def render_problem_visual(ctx: RenderContext, points: List[str]) -> None:
    bounds = content_bounds_for_slide(ctx)
    pairs = [(f"Вызов {i + 1}", p) for i, p in enumerate(points[:4])]
    render_equal_cells_stack(ctx, bounds, pairs, accent_index=0)


def render_goals_visual(ctx: RenderContext, goals: List[str]) -> None:
    bounds = content_bounds_for_slide(ctx)
    items = [(f"Цель {i + 1}", g, f"Ц{i + 1}") for i, g in enumerate(goals[:3])]
    render_equal_cells_row(
        ctx,
        left_pct=bounds.left_pct,
        top_pct=bounds.top_pct,
        width_pct=bounds.right_pct - bounds.left_pct,
        height_pct=bounds.bottom_pct - bounds.top_pct,
        items=items,
    )
