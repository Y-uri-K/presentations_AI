from __future__ import annotations

import logging

from fastapi import HTTPException, status

from app.ai.types import ChatMessage
from app.services.template_driven.blueprint_llm import chat_for_blueprint
from app.config import get_settings
from app.schemas.template_blueprint import PresentationBlueprint, TemplateCatalog
from app.services.ai_json import extract_json
from app.services.presentation_gamma.outline import parse_outline_chunks, strip_title_tag
from app.services.template_driven.layout_matcher import assign_template_layouts
from app.services.template_driven.prompts import blueprint_phase1_prompt, blueprint_phase2_prompt

logger = logging.getLogger(__name__)
settings = get_settings()


def _catalog_for_prompt(catalog: TemplateCatalog) -> str:
    """Компактный каталог — меньше токенов и быстрее ответ LLM."""
    import json

    payload = [
        {
            "template_key": slide.template_key,
            "slide_type": slide.slide_type,
            "layout_name": slide.layout_name,
            "slots": len(slide.content_slots),
            "cards": len(slide.card_slots),
            "table": slide.has_table,
            "timeline": slide.has_timeline,
        }
        for slide in catalog.slides
    ]
    return json.dumps(payload, ensure_ascii=False, indent=2)


async def generate_blueprint_phase1(
    *,
    agent_id: str,
    title: str,
    outline: str,
    catalog: TemplateCatalog,
    presentation_prompt: str | None,
) -> PresentationBlueprint:
    chunks = parse_outline_chunks(outline)
    body = strip_title_tag(outline)
    prompt = blueprint_phase1_prompt(
        title=title,
        outline="\n\n".join(chunks) if chunks else body,
        catalog_json=_catalog_for_prompt(catalog),
        presentation_prompt=presentation_prompt,
    )
    raw = await chat_for_blueprint(agent_id, [ChatMessage(role="user", content=prompt)])
    try:
        data = extract_json(raw)
        blueprint = PresentationBlueprint.model_validate(data)
    except Exception as exc:
        logger.warning("Blueprint phase1 parse failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Не удалось разобрать blueprint (этап 1): {exc}",
        ) from exc

    blueprint.title = blueprint.title or title
    blueprint.slides = blueprint.slides[: settings.presentation_max_slides]
    assign_template_layouts(blueprint, catalog)
    from app.services.template_driven.blueprint_normalize import normalize_blueprint_slides

    normalize_blueprint_slides(blueprint, catalog=catalog)
    return blueprint


async def generate_blueprint_phase2(
    *,
    agent_id: str,
    blueprint: PresentationBlueprint,
    catalog: TemplateCatalog,
    issues: str,
) -> PresentationBlueprint:
    import json

    prompt = blueprint_phase2_prompt(
        blueprint_json=blueprint.model_dump_json(indent=2),
        catalog_json=_catalog_for_prompt(catalog),
        issues=issues,
    )
    raw = await chat_for_blueprint(agent_id, [ChatMessage(role="user", content=prompt)])
    try:
        data = extract_json(raw)
        return PresentationBlueprint.model_validate(data)
    except Exception as exc:
        logger.warning("Blueprint phase2 parse failed, keep phase1: %s", exc)
        return blueprint
