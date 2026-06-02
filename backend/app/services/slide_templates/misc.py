from __future__ import annotations

from app.schemas.semantic_slides import (
    AgendaSlide,
    ConclusionSlide,
    GoalsSlide,
    ProblemSlide,
    TableSlide,
    ThankYouSlide,
    TitleSlide,
)
from app.services.slide_renderers.context import RenderContext
from app.services.slide_renderers.drawing import add_logo_zone_marker, add_subtitle, add_table, add_title
from app.services.slide_renderers.layout_bounds import content_bounds_for_slide
from app.services.slide_templates._helpers import render_cards_horizontal, render_sidebar_list, render_with_title
from app.services.slide_templates.image_layouts import render_image_column_texts
from app.services.slide_templates.visual_layouts import (
    render_dense_grid,
    render_goals_visual,
    render_problem_visual,
    render_visual_agenda,
    render_visual_conclusion,
)


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
    elif variant in ("visual_path", "numbered_path", "grid"):
        render_visual_agenda(ctx, spec.items[:6])
    else:
        render_visual_agenda(ctx, spec.items[:6])


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
    elif variant in ("visual_ladder", "severity_ladder", "visual_grid"):
        render_problem_visual(ctx, points)
    else:
        render_problem_visual(ctx, points)


def render_goals(ctx: RenderContext, variant: str) -> None:
    spec: GoalsSlide = ctx.spec  # type: ignore[assignment]
    goals = spec.goals[:5]
    if variant == "image_column" or ctx.has_image_zone:
        render_image_column_texts(ctx, goals, prefix="◎")
        return
    render_with_title(ctx)
    if variant in ("target_rings", "hero_featured"):
        render_goals_visual(ctx, goals)
    elif variant == "visual_grid":
        items = [type("C", (), {"title": f"Цель {i + 1}", "text": g, "highlight": False})() for i, g in enumerate(goals)]
        render_dense_grid(ctx, items)
    else:
        render_goals_visual(ctx, goals)


def render_conclusion(ctx: RenderContext, variant: str) -> None:
    spec: ConclusionSlide = ctx.spec  # type: ignore[assignment]
    takeaways = spec.takeaways[:5]
    if variant == "image_column" or ctx.has_image_zone:
        render_image_column_texts(ctx, takeaways, prefix="✓")
        return
    render_with_title(ctx)
    if variant in ("visual_stack", "stack", "full_banners", "numbered", "checklist"):
        render_visual_conclusion(ctx, takeaways)
    else:
        render_visual_conclusion(ctx, takeaways)


def render_table(ctx: RenderContext, variant: str) -> None:
    spec: TableSlide = ctx.spec  # type: ignore[assignment]
    render_with_title(ctx)
    if variant == "compact":
        top = 0.28
    elif variant == "striped":
        top = 0.31
    else:
        top = 0.32
    add_table(ctx, spec.table.headers, spec.table.rows, top_pct=top)
