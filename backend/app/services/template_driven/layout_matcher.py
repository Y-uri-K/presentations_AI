from __future__ import annotations

from typing import List

from app.schemas.template_blueprint import BlueprintSlide, PresentationBlueprint, TemplateCatalog
from app.services.template_driven.constants import MAX_SAME_LAYOUT_IN_ROW


def _outline_topic_type(topic: str) -> str:
    lowered = topic.lower()
    if any(w in lowered for w in ("сравнен", "vs", "против", "до/после")):
        return "comparison"
    if any(w in lowered for w in ("этап", "шаг", "процесс", "timeline", "фаза")):
        return "timeline"
    if any(w in lowered for w in ("таблиц", "столбц", "строк")):
        return "table"
    if any(
        w in lowered
        for w in (
            "%",
            "метрик",
            "kpi",
            "показател",
            "рост",
            "анализ",
            "аналитик",
            "статистик",
            "данн",
            "график",
            "chart",
            "dashboard",
        )
    ):
        return "kpi"
    if any(w in lowered for w in ("диаграм", "схем", "график", "архитектур")):
        return "diagram"
    if any(w in lowered for w in ("преимуществ", "недостат", "функци", "тип")):
        return "cards"
    return "title_content"


def _content_backed_type(slide: BlueprintSlide) -> str | None:
    if slide.cards:
        return "cards"
    if slide.metrics:
        return "kpi"
    if slide.timeline_steps:
        return "timeline"
    if slide.process_steps:
        return "process"
    if slide.table:
        return "table"
    if slide.comparison:
        return "comparison"
    if slide.key_points:
        return "diagram"
    if slide.slide_type == "conclusion" and slide.bullets:
        return "conclusion"
    return None


def assign_template_layouts(blueprint: PresentationBlueprint, catalog: TemplateCatalog) -> None:
    recent_types: List[str] = []

    for slide in blueprint.slides:
        backed = _content_backed_type(slide)
        desired = backed or slide.slide_type or _outline_topic_type(slide.topic or slide.title)
        analytics_locked = desired in ("kpi", "table") or backed in ("kpi", "table")
        if (
            not analytics_locked
            and len(recent_types) >= MAX_SAME_LAYOUT_IN_ROW
            and all(t == desired for t in recent_types[-MAX_SAME_LAYOUT_IN_ROW:])
        ):
            for alternate in ("cards", "comparison", "timeline", "diagram", "process"):
                if alternate != desired:
                    desired = alternate  # type: ignore[assignment]
                    break

        candidates = catalog.candidates(desired)
        if not candidates:
            candidates = catalog.slides
        slide.slide_type = desired  # type: ignore[assignment]
        pick_index = len(recent_types) % len(candidates)
        slide.template_key = candidates[pick_index].template_key
        recent_types.append(desired)
