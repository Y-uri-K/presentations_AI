from __future__ import annotations

import logging
import time
from typing import Dict, Tuple

from app.config import get_settings
from app.schemas.slides import PresentationSlides
from app.schemas.template_blueprint import PresentationBlueprint
from app.services.template_driven.blueprint_converter import blueprint_to_presentation_slides
from app.services.template_driven.blueprint_generator import (
    generate_blueprint_phase1,
    generate_blueprint_phase2,
)
from app.services.template_driven.blueprint_validator import validate_blueprint
from app.services.template_driven.blueprint_normalize import normalize_blueprint_slides
from app.services.template_driven.layout_matcher import assign_template_layouts
from app.services.template_driven.post_validator import validate_filled_pptx
from app.services.template_driven.pptx_filler import fill_template_pptx
from app.services.template_driven.outline_blueprint import blueprint_from_outline
from app.services.template_driven.structure_analyzer import AnalyzedTemplate, analyze_template_structure
from app.services.template_style_service import resolve_user_template_style

logger = logging.getLogger(__name__)
settings = get_settings()


async def analyze_template_for_build(template_bytes: bytes) -> AnalyzedTemplate:
    """Структура макетов + Polza-стиль (без blueprint LLM)."""
    started = time.perf_counter()
    analyzed = analyze_template_structure(template_bytes)
    logger.info(
        "Структура шаблона: %s макетов за %.1f с",
        len(analyzed.catalog.slides),
        time.perf_counter() - started,
    )

    if settings.presentation_template_ai_analysis:
        style_started = time.perf_counter()
        analyzed.user_style = await resolve_user_template_style(
            template_bytes,
            "pptx",
            catalog=analyzed.catalog,
        )
        logger.info(
            "AI-стиль шаблона (Polza): %.1f с, палитра=%s",
            time.perf_counter() - style_started,
            ", ".join(analyzed.user_style.palette_hex[:6])
            if analyzed.user_style.palette_hex
            else "—",
        )

    logger.info("Анализ шаблона всего: %.1f с", time.perf_counter() - started)
    return analyzed


async def generate_presentation_blueprint(
    analyzed: AnalyzedTemplate,
    *,
    agent_id: str,
    outline: str,
    title: str,
    presentation_prompt: str | None,
) -> Tuple[PresentationBlueprint, PresentationSlides]:
    """Привязка плана к макетам шаблона (+ опционально LLM)."""
    started = time.perf_counter()
    if settings.presentation_blueprint_use_llm:
        try:
            blueprint = await generate_blueprint_phase1(
                agent_id=agent_id,
                title=title,
                outline=outline,
                catalog=analyzed.catalog,
                presentation_prompt=presentation_prompt,
            )
        except Exception as exc:
            logger.warning("Blueprint LLM недоступен (%s), сборка из плана", exc)
            blueprint = blueprint_from_outline(
                outline=outline, title=title, catalog=analyzed.catalog
            )
    else:
        logger.info("Blueprint из готового плана (LLM отключён, PRESENTATION_BLUEPRINT_USE_LLM=false)")
        blueprint = blueprint_from_outline(
            outline=outline, title=title, catalog=analyzed.catalog
        )
    normalize_blueprint_slides(blueprint, catalog=analyzed.catalog)
    report = validate_blueprint(blueprint, analyzed.catalog)
    if not report.ok and settings.presentation_blueprint_llm_phase2:
        issue_text = "\n".join(
            f"Слайд {i.slide_index + 1}: {i.field} — {i.message}" for i in report.issues[:20]
        )
        try:
            blueprint = await generate_blueprint_phase2(
                agent_id=agent_id,
                blueprint=blueprint,
                catalog=analyzed.catalog,
                issues=issue_text,
            )
            assign_template_layouts(blueprint, analyzed.catalog)
            normalize_blueprint_slides(blueprint, catalog=analyzed.catalog)
        except Exception as exc:
            logger.warning("Blueprint LLM этап 2 пропущен: %s", exc)
        validate_blueprint(blueprint, analyzed.catalog)

    normalize_blueprint_slides(blueprint, catalog=analyzed.catalog)
    logger.info(
        "Blueprint: %s слайдов за %.1f с",
        len(blueprint.slides),
        time.perf_counter() - started,
    )
    return blueprint, blueprint_to_presentation_slides(blueprint)


async def prepare_presentation_blueprint(
    *,
    agent_id: str,
    template_bytes: bytes,
    outline: str,
    title: str,
    presentation_prompt: str | None,
) -> Tuple[AnalyzedTemplate, PresentationBlueprint, PresentationSlides]:
    """Полный цикл: анализ шаблона + blueprint (для тестов и совместимости)."""
    analyzed = await analyze_template_for_build(template_bytes)
    blueprint, slides = await generate_presentation_blueprint(
        analyzed,
        agent_id=agent_id,
        outline=outline,
        title=title,
        presentation_prompt=presentation_prompt,
    )
    return analyzed, blueprint, slides


async def build_presentation_from_template_blueprint(
    *,
    agent_id: str,
    template_bytes: bytes,
    outline: str,
    title: str,
    presentation_prompt: str | None,
    slide_images: Dict[int, bytes],
) -> Tuple[bytes, PresentationSlides, PresentationBlueprint]:
    started = time.perf_counter()
    analyzed = await analyze_template_for_build(template_bytes)
    blueprint, slides = await generate_presentation_blueprint(
        analyzed,
        agent_id=agent_id,
        outline=outline,
        title=title,
        presentation_prompt=presentation_prompt,
    )
    pptx_bytes = fill_template_pptx(template_bytes, analyzed, blueprint, slide_images)

    pptx_issues = validate_filled_pptx(pptx_bytes)
    if pptx_issues:
        logger.warning("Пост-валидация PPTX: %s проблем, повтор этапа 2", len(pptx_issues))
        issue_text = "\n".join(
            f"Слайд {i.slide_index + 1}: {i.reason}" for i in pptx_issues[:15]
        )
        blueprint = await generate_blueprint_phase2(
            agent_id=agent_id,
            blueprint=blueprint,
            catalog=analyzed.catalog,
            issues=issue_text,
        )
        assign_template_layouts(blueprint, analyzed.catalog)
        slides = blueprint_to_presentation_slides(blueprint)
        pptx_bytes = fill_template_pptx(template_bytes, analyzed, blueprint, slide_images)

    logger.info("Template-driven сборка за %.1f с", time.perf_counter() - started)
    return pptx_bytes, slides, blueprint
