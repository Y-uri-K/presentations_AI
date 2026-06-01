from __future__ import annotations

from app.schemas.semantic_slides import (
    AgendaSlide,
    ConclusionSlide,
    ProblemSlide,
    TableSlide,
    ThankYouSlide,
    TitleSlide,
)
from app.services.slide_renderers.context import RenderContext
from app.services.slide_renderers.drawing import add_card, add_logo_zone_marker, add_subtitle, add_table, add_title
from app.services.slide_renderers.layout_bounds import content_bounds_for_slide
from app.services.slide_templates._helpers import (
    render_cards_grid,
    render_cards_horizontal,
    render_sidebar_list,
    render_with_title,
)
from app.services.slide_templates.image_layouts import render_image_column_texts


def render_title(ctx: RenderContext, variant: str) -> None:
    spec: TitleSlide = ctx.spec  # type: ignore[assignment]
    pattern = ctx.user_style.title_layout_pattern or "title_center"
    add_logo_zone_marker(ctx)
    del variant

    if pattern == "title_hero_right":
        add_title(ctx, top_pct=0.30, height_pct=0.18)
        if spec.subtitle:
            add_subtitle(ctx, spec.subtitle, top_pct=0.50)
    elif pattern == "title_hero_left":
        add_title(ctx, top_pct=0.32, height_pct=0.18)
        if spec.subtitle:
            add_subtitle(ctx, spec.subtitle, top_pct=0.52)
    elif pattern == "title_logo_top":
        add_title(ctx, top_pct=0.38, height_pct=0.16)
        if spec.subtitle:
            add_subtitle(ctx, spec.subtitle, top_pct=0.56)
    else:
        add_title(ctx, top_pct=0.28, height_pct=0.18)
        if spec.subtitle:
            add_subtitle(ctx, spec.subtitle, top_pct=0.48)


def render_thank_you(ctx: RenderContext, variant: str) -> None:
    spec: ThankYouSlide = ctx.spec  # type: ignore[assignment]
    del variant
    add_title(ctx, top_pct=0.32, height_pct=0.2)
    if spec.subtitle:
        add_subtitle(ctx, spec.subtitle, top_pct=0.52)
    if spec.contact:
        add_subtitle(ctx, spec.contact, top_pct=0.64)


def render_agenda(ctx: RenderContext, variant: str) -> None:
    spec: AgendaSlide = ctx.spec  # type: ignore[assignment]
    if variant == "image_column" or ctx.has_image_zone:
        render_image_column_texts(ctx, spec.items[:6], prefix="")
        return
    render_with_title(ctx)
    if variant == "vertical_list":
        render_sidebar_list(ctx, [(f"{i + 1}", item) for i, item in enumerate(spec.items[:6])])
    elif variant == "numbered_path":
        bounds = content_bounds_for_slide(ctx)
        step = (bounds.bottom_pct - bounds.top_pct) / max(len(spec.items), 1)
        for index, item in enumerate(spec.items[:6]):
            add_card(
                ctx,
                left_pct=bounds.left_pct + 0.04 * (index % 2),
                top_pct=bounds.top_pct + index * step,
                width_pct=bounds.right_pct - bounds.left_pct - 0.04 * (index % 2),
                height_pct=step * 0.9,
                heading=f"{index + 1}",
                body=item,
                accent=index == 0,
                style="sidebar",
            )
    else:
        items = [type("I", (), {"title": str(i + 1), "text": t, "highlight": i == 0})() for i, t in enumerate(spec.items[:6])]
        render_cards_grid(ctx, items, heading_fn=lambda i: str(i + 1))


def render_problem(ctx: RenderContext, variant: str) -> None:
    spec: ProblemSlide = ctx.spec  # type: ignore[assignment]
    if variant == "image_column" or ctx.has_image_zone:
        render_image_column_texts(ctx, spec.pain_points[:6], prefix="!")
        return
    render_with_title(ctx)
    points = spec.pain_points[:6]
    if variant == "accent_row":
        render_cards_horizontal(
            ctx,
            [type("C", (), {"title": f"Вызов {i + 1}", "text": p, "highlight": False})() for i, p in enumerate(points)],
        )
    elif variant == "severity_ladder":
        from app.services.slide_templates._helpers import render_sidebar_list

        render_sidebar_list(ctx, [(f"Риск {i + 1}", p) for i, p in enumerate(points[:4])])
    else:
        items = [type("C", (), {"title": f"Вызов {i + 1}", "text": p, "highlight": i == 0})() for i, p in enumerate(points)]
        render_cards_grid(ctx, items)


def render_conclusion(ctx: RenderContext, variant: str) -> None:
    spec: ConclusionSlide = ctx.spec  # type: ignore[assignment]
    takeaways = spec.takeaways[:5]
    if variant == "image_column" or ctx.has_image_zone:
        render_image_column_texts(ctx, takeaways, prefix="✓")
        return
    render_with_title(ctx)
    bounds = content_bounds_for_slide(ctx)

    if variant == "full_banners":
        step = (bounds.bottom_pct - bounds.top_pct) / max(len(takeaways), 1)
        for index, text in enumerate(takeaways):
            add_card(
                ctx,
                left_pct=bounds.left_pct,
                top_pct=bounds.top_pct + index * step,
                width_pct=bounds.right_pct - bounds.left_pct,
                height_pct=step * 0.92,
                heading="Вывод",
                body=text,
                accent=index == 0,
                style="rectangle" if index % 2 else "sidebar",
            )
    elif variant == "numbered":
        render_sidebar_list(ctx, [(f"Вывод {i + 1}", t) for i, t in enumerate(takeaways)])
    elif variant == "checklist":
        bounds = content_bounds_for_slide(ctx)
        step = (bounds.bottom_pct - bounds.top_pct) / max(len(takeaways), 1)
        for index, text in enumerate(takeaways):
            add_card(
                ctx,
                left_pct=bounds.left_pct,
                top_pct=bounds.top_pct + index * step,
                width_pct=bounds.right_pct - bounds.left_pct,
                height_pct=step * 0.9,
                heading="✓",
                body=text,
                accent=index == 0,
                style="flat",
            )
    else:
        step = (bounds.bottom_pct - bounds.top_pct) / max(len(takeaways), 1)
        for index, text in enumerate(takeaways):
            add_card(
                ctx,
                left_pct=bounds.left_pct,
                top_pct=bounds.top_pct + index * step,
                width_pct=bounds.right_pct - bounds.left_pct,
                height_pct=step * 0.92,
                heading="•",
                body=text,
                accent=index == 0,
                style="rounded",
            )


def render_table(ctx: RenderContext, variant: str) -> None:
    spec: TableSlide = ctx.spec  # type: ignore[assignment]
    render_with_title(ctx)
    if variant == "compact":
        top = 0.28
    elif variant == "key_column":
        top = 0.30
    elif variant == "striped":
        top = 0.31
    else:
        top = 0.32
    add_table(ctx, spec.table.headers, spec.table.rows, top_pct=top)
