from __future__ import annotations

import logging
import time
from datetime import datetime
from typing import List, Optional

from fastapi import HTTPException, status

from app.ai.registry import chat_with_agent_resilient
from app.ai.types import ChatMessage
from app.config import get_settings
from app.schemas.slides import PresentationSlides
from app.services.presentation_gamma.outline import parse_outline_chunks
from app.services.presentation_gamma.prompts import slides_xml_system_prompt
from app.services.presentation_gamma.xml_parser import xml_to_presentation_slides
from app.services.semantic_slide_planner import (
    _merge_plan_types,
    _semantic_plan_from_slides_raw,
)
from app.services.slide_quality import score_presentation

settings = get_settings()
logger = logging.getLogger(__name__)


def _format_slides_prompt(
    *,
    title: str,
    prompt: str,
    outline_chunks: List[str],
    language: str,
    tone: str,
    text_content: str,
    audience: str,
    scenario: str,
    search_results: str,
) -> str:
    current_date = datetime.now().strftime("%d %B %Y")
    template = slides_xml_system_prompt()
    return (
        template.replace("{title}", title)
        .replace("{prompt}", prompt or "—")
        .replace("{current_date}", current_date)
        .replace("{language}", language)
        .replace("{tone}", tone)
        .replace("{text_content}", text_content)
        .replace("{audience}", audience)
        .replace("{scenario}", scenario)
        .replace("{total_slides}", str(len(outline_chunks)))
        .replace("{outline_formatted}", "\n\n".join(outline_chunks))
        .replace(
            "{search_results}",
            search_results if search_results else "Дополнительных исследований нет.",
        )
    )


async def generate_slides_from_xml(
    *,
    agent_id: str,
    title: str,
    prompt: Optional[str],
    outline_md: str,
    template_name: Optional[str] = None,
    presentation_prompt: Optional[str] = None,
) -> PresentationSlides:
    """
    Фаза 2 (как presentation-ai): outline[] → LLM → XML → PresentationSlides.
    """
    outline_chunks = parse_outline_chunks(outline_md)
    if not outline_chunks:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="План пустой — добавьте темы слайдов",
        )

    user_prompt = presentation_prompt or prompt or ""
    if template_name:
        user_prompt = f"{user_prompt}\nШаблон оформления: «{template_name}».".strip()

    system_user = _format_slides_prompt(
        title=title,
        prompt=user_prompt,
        outline_chunks=outline_chunks,
        language=settings.presentation_language,
        tone=settings.presentation_tone,
        text_content=settings.presentation_text_content,
        audience=settings.presentation_audience,
        scenario=settings.presentation_scenario,
        search_results="",
    )

    logger.info(
        "Gamma XML: генерация %s слайдов (агент=%s)...",
        len(outline_chunks),
        agent_id,
    )
    started = time.perf_counter()
    raw_xml = await chat_with_agent_resilient(
        agent_id,
        [ChatMessage(role="user", content=system_user)],
    )
    logger.info("Gamma XML: ответ за %.1f с", time.perf_counter() - started)

    try:
        presentation = xml_to_presentation_slides(raw_xml)
    except Exception as exc:
        logger.warning("Gamma XML parse failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Не удалось разобрать XML презентации: {exc}",
        ) from exc

    if len(presentation.slides) > settings.presentation_max_slides:
        presentation.slides = presentation.slides[: settings.presentation_max_slides]

    report = score_presentation(presentation)
    if not report.passes:
        logger.info("Gamma: локальная донастройка типов (score=%.3f)", report.average_score)
        plan = _semantic_plan_from_slides_raw(
            [s.model_dump() for s in presentation.slides]
        )
        presentation = _merge_plan_types(presentation, plan)

    logger.info(
        "Gamma XML: готово %s слайдов, типы=%s",
        len(presentation.slides),
        [s.type for s in presentation.slides],
    )
    return presentation
