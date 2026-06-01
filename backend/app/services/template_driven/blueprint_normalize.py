from __future__ import annotations

import logging
from typing import Optional

from app.schemas.template_blueprint import BlueprintCard, PresentationBlueprint, TemplateCatalog
from app.services.slide_text_limits import card_title_from_text

logger = logging.getLogger(__name__)

_SEMANTIC_MAX_CARDS = 6
_SEMANTIC_MAX_TIMELINE = 7
_SEMANTIC_MAX_PROCESS = 6
_SEMANTIC_MAX_COMPARISON_POINTS = 5
_SEMANTIC_MAX_TABLE_HEADERS = 6
_SEMANTIC_MAX_TABLE_ROWS = 8
_SEMANTIC_MAX_METRICS = 6
_SEMANTIC_MAX_KEY_POINTS = 4


def _max_cards_for_slide(catalog: Optional[TemplateCatalog], template_key: str) -> int:
    limit = _SEMANTIC_MAX_CARDS
    if catalog is None:
        return limit
    tpl = catalog.by_key(template_key)
    if tpl and tpl.card_slots:
        limit = min(limit, len(tpl.card_slots))
    return max(2, limit)


def normalize_blueprint_slides(
    blueprint: PresentationBlueprint,
    catalog: Optional[TemplateCatalog] = None,
) -> None:
    """Приводит blueprint к лимитам semantic_slides и макета шаблона."""
    for slide in blueprint.slides:
        max_cards = _max_cards_for_slide(catalog, slide.template_key)

        if slide.slide_type == "cards" and len(slide.cards) < 2:
            if slide.bullets:
                slide.cards = [
                    BlueprintCard(
                        title=card_title_from_text(text, index=index),
                        text=text,
                    )
                    for index, text in enumerate(slide.bullets[:max_cards], start=1)
                ]
            while len(slide.cards) < 2:
                slide.cards.append(
                    BlueprintCard(
                        title=f"Пункт {len(slide.cards) + 1}",
                        text=slide.subtitle or slide.title or "Содержание слайда.",
                    )
                )

        if len(slide.cards) > max_cards:
            logger.warning(
                "Слайд %s: обрезано карточек %s → %s (макет %s)",
                slide.title[:40],
                len(slide.cards),
                max_cards,
                slide.template_key,
            )
            slide.cards = slide.cards[:max_cards]

        if slide.comparison:
            slide.comparison.left_points = slide.comparison.left_points[:_SEMANTIC_MAX_COMPARISON_POINTS]
            slide.comparison.right_points = slide.comparison.right_points[:_SEMANTIC_MAX_COMPARISON_POINTS]

        slide.timeline_steps = slide.timeline_steps[:_SEMANTIC_MAX_TIMELINE]
        slide.process_steps = slide.process_steps[:_SEMANTIC_MAX_PROCESS]
        slide.metrics = slide.metrics[:_SEMANTIC_MAX_METRICS]
        slide.key_points = slide.key_points[:_SEMANTIC_MAX_KEY_POINTS]
        slide.bullets = slide.bullets[:_SEMANTIC_MAX_CARDS]

        if slide.table:
            slide.table.headers = slide.table.headers[:_SEMANTIC_MAX_TABLE_HEADERS]
            slide.table.rows = slide.table.rows[:_SEMANTIC_MAX_TABLE_ROWS]

        if slide.slide_type == "title" and not slide.subtitle and slide.bullets:
            slide.subtitle = " ".join(slide.bullets[:2])[:200]

        if slide.slide_type == "conclusion":
            if not slide.bullets:
                if slide.cards:
                    slide.bullets = [f"{c.title}: {c.text}" for c in slide.cards[:5]]
                elif slide.subtitle:
                    slide.bullets = [slide.subtitle]
            while len(slide.bullets) < 2:
                slide.bullets.append(slide.title or f"Итог {len(slide.bullets) + 1}")

        if slide.slide_type == "title_content" and not slide.cards and not slide.bullets:
            slide.bullets = [slide.subtitle or slide.title or "Содержание слайда"]

        if slide.slide_type in ("kpi", "metrics") and not slide.metrics and slide.bullets:
            from app.services.analytics_outline import extract_metrics_from_bullets

            slide.metrics = extract_metrics_from_bullets(slide.bullets)

        if slide.slide_type == "table" and slide.bullets and not slide.table:
            from app.services.analytics_outline import extract_table_from_bullets

            parsed = extract_table_from_bullets(slide.bullets)
            if parsed:
                slide.table = parsed
