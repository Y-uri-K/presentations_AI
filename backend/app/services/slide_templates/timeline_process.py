from __future__ import annotations

from app.schemas.semantic_slides import ProcessSlide, TimelineSlide
from app.services.slide_renderers.context import RenderContext
from app.services.slide_renderers.content_cell import render_equal_cells_row, render_equal_cells_stack
from app.services.slide_renderers.drawing import add_horizontal_timeline
from app.services.slide_renderers.layout_bounds import content_bounds_for_slide
from app.services.slide_templates._helpers import render_sidebar_list, render_with_title


def _vertical_rail(ctx: RenderContext, steps: list) -> None:
    bounds = content_bounds_for_slide(ctx)
    pairs = [
        (label, f"{description}".strip() if description else label)
        for label, description in steps[:6]
    ]
    render_equal_cells_stack(ctx, bounds, pairs, max_items=5)


def render_timeline(ctx: RenderContext, variant: str) -> None:
    spec: TimelineSlide = ctx.spec  # type: ignore[assignment]
    steps = [(s.label, s.description or "") for s in spec.steps]
    if variant == "image_column" or ctx.has_image_zone:
        from app.services.slide_templates.image_layouts import render_image_column_texts

        render_image_column_texts(
            ctx,
            [f"{label}: {desc}" if desc else label for label, desc in steps[:6]],
        )
        return

    render_with_title(ctx)
    bounds = content_bounds_for_slide(ctx)
    span_w = bounds.right_pct - bounds.left_pct
    span_h = bounds.bottom_pct - bounds.top_pct

    if variant == "vertical_rail":
        _vertical_rail(ctx, steps)
    elif variant in ("step_cards", "milestones"):
        count = min(len(steps), 4 if variant == "milestones" else 5)
        items = [
            (
                f"Шаг {index + 1}" if variant == "step_cards" else f"M{index + 1}",
                f"{label}\n{description or ''}".strip(),
                None,
            )
            for index, (label, description) in enumerate(steps[:count])
        ]
        render_equal_cells_row(
            ctx,
            left_pct=bounds.left_pct,
            top_pct=bounds.top_pct,
            width_pct=span_w,
            height_pct=span_h,
            items=items,
            accent_index=count - 1,
        )
    else:
        add_horizontal_timeline(ctx, steps)


def render_process(ctx: RenderContext, variant: str) -> None:
    spec: ProcessSlide = ctx.spec  # type: ignore[assignment]
    steps = [(s.title, s.description or "") for s in spec.steps]
    if variant == "image_column" or ctx.has_image_zone:
        from app.services.slide_templates.image_layouts import render_image_column_texts

        render_image_column_texts(
            ctx,
            [f"{title}: {desc}" if desc else title for title, desc in steps[:4]],
        )
        return

    render_with_title(ctx)
    bounds = content_bounds_for_slide(ctx)

    if variant == "vertical_pipe":
        _vertical_rail(ctx, steps)
    elif variant == "step_badges":
        render_sidebar_list(
            ctx,
            [(f"{i + 1}. {title}", description or "") for i, (title, description) in enumerate(steps[:5])],
        )
    elif variant == "funnel":
        levels = min(len(steps), 4)
        pairs = [(title, description or "") for title, description in steps[:levels]]
        render_equal_cells_stack(ctx, bounds, pairs, accent_index=0, max_items=levels)
    else:
        count = min(len(steps), 4)
        items = [
            (f"Этап {index + 1}", f"{title}\n{description or ''}".strip(), None)
            for index, (title, description) in enumerate(steps[:count])
        ]
        render_equal_cells_row(
            ctx,
            left_pct=bounds.left_pct,
            top_pct=bounds.top_pct,
            width_pct=bounds.right_pct - bounds.left_pct,
            height_pct=bounds.bottom_pct - bounds.top_pct,
            items=items,
            accent_index=count - 1,
        )
