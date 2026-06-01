from __future__ import annotations

import logging

from app.services.slide_renderers.context import RenderContext
from app.services.slide_templates import cards, comparison_kpi, diagram, misc, timeline_process

logger = logging.getLogger(__name__)

_RENDERERS = {
    "title": misc.render_title,
    "thank_you": misc.render_thank_you,
    "agenda": misc.render_agenda,
    "problem": misc.render_problem,
    "goals": lambda ctx, v: cards.render_cards(ctx, v if v != "default" else "featured"),
    "cards": cards.render_cards,
    "comparison": comparison_kpi.render_comparison,
    "timeline": timeline_process.render_timeline,
    "process": timeline_process.render_process,
    "kpi": comparison_kpi.render_kpi,
    "results": comparison_kpi.render_results,
    "table": misc.render_table,
    "diagram": diagram.render_diagram,
    "conclusion": misc.render_conclusion,
}


def render_slide_with_template(ctx: RenderContext) -> None:
    slide_type = ctx.spec.type
    variant = ctx.layout_variant or "default"
    renderer = _RENDERERS.get(slide_type)
    if renderer is None:
        logger.debug("Шаблон слайда: fallback cards для type=%s", slide_type)
        cards.render_cards(ctx, "grid")
        return
    logger.debug("Шаблон слайда %s: type=%s variant=%s", ctx.slide_index + 1, slide_type, variant)
    renderer(ctx, variant)
