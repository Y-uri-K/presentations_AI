from __future__ import annotations

import logging
import time
from typing import List, Optional

from fastapi import HTTPException, status

from app.config import get_settings
from app.schemas.slides import PresentationSlides
from app.services.presentation_gamma.generator import generate_slides_from_xml
from app.services.presentation_gamma.outline import extract_presentation_title
from app.services.semantic_slide_planner import plan_slides_with_quality_loop
from app.services.slide_quality import score_presentation
from app.services.source_image_extractor import list_available_image_refs

settings = get_settings()
logger = logging.getLogger(__name__)


async def plan_slides_from_outline(
    *,
    agent_id: str,
    outline: str,
    available_image_refs: List[str],
    template_name: Optional[str] = None,
    presentation_prompt: Optional[str] = None,
    presentation_title: Optional[str] = None,
) -> PresentationSlides:
    """
    Алгоритм как в presentation-ai (ALLWEONE):
    1) план markdown + <TITLE>
    2) LLM → XML <PRESENTATION><SECTION>…
    3) парсер → semantic JSON → PPTX renderers

    При ошибке XML — fallback на legacy JSON-планировщик.
    """
    started = time.perf_counter()
    title = presentation_title or extract_presentation_title(
        outline, fallback=presentation_prompt or "Презентация"
    )

    if settings.presentation_use_gamma_pipeline:
        try:
            presentation = await generate_slides_from_xml(
                agent_id=agent_id,
                title=title,
                prompt=presentation_prompt,
                outline_md=outline,
                template_name=template_name,
                presentation_prompt=presentation_prompt,
            )
            report = score_presentation(presentation)
            logger.info(
                "Планирование (gamma): %s слайдов, score=%.3f, %.1f с",
                len(presentation.slides),
                report.average_score,
                time.perf_counter() - started,
            )
            return presentation
        except HTTPException as exc:
            if exc.status_code not in (
                status.HTTP_502_BAD_GATEWAY,
                status.HTTP_503_SERVICE_UNAVAILABLE,
            ):
                raise
            logger.warning("Gamma pipeline failed (%s), legacy fallback", exc.detail)

    presentation = await plan_slides_with_quality_loop(
        agent_id=agent_id,
        outline=outline,
        available_image_refs=available_image_refs,
        template_name=template_name,
        presentation_prompt=presentation_prompt,
    )
    report = score_presentation(presentation)
    logger.info(
        "Планирование (legacy): %s слайдов, score=%.3f, %.1f с",
        len(presentation.slides),
        report.average_score,
        time.perf_counter() - started,
    )
    return presentation


def available_refs_from_sources(sources: List[tuple[str, bytes]]) -> List[str]:
    return list_available_image_refs(sources)
