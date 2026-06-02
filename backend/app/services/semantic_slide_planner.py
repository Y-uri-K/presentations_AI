from __future__ import annotations

import json
import logging
import time
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, status

from app.ai.registry import chat_with_agent_resilient
from app.ai.types import ChatMessage
from app.config import get_settings
from app.schemas.semantic_slides import PresentationSlides, SemanticPlan, SemanticPlanItem
from app.services.slide_layout_selector import apply_layout_rules, coerce_away_bullet_layout
from app.services.slide_payload_normalizer import normalize_slide_payload
from app.services.ai_json import extract_json
from app.services.slide_quality import QUALITY_THRESHOLD, score_presentation

settings = get_settings()
logger = logging.getLogger(__name__)

UNIFIED_SLIDES_PROMPT = """Ты арт-директор презентаций уровня McKinsey/Apple Keynote. По плану создай JSON слайдов с МАКСИМАЛЬНОЙ визуальной плотностью.

Верни ТОЛЬКО JSON:
{{
  "slides": [
    {{
      "type": "title|agenda|problem|goals|kpi|cards|comparison|timeline|process|results|table|diagram|conclusion|thank_you",
      "title": "заголовок",
      ...поля по типу...
    }}
  ]
}}

Поля по типам:
- title: subtitle?
- agenda: items[] (4–7)
- problem: pain_points[] (3–5) — конкретные риски/боли
- goals: goals[] (3–5) — измеримые формулировки
- kpi: metrics[] {{value, label, note?}} — value с цифрами/%% где возможно
- cards: cards[] {{title, text, highlight?}} — highlight = ключевая цифра или факт
- comparison: left {{heading, points[]}}, right {{heading, points[]}}
- timeline: steps[] {{label, description?}}
- process: steps[] {{title, description?}}
- results: results[] {{label, value, trend?}}, summary?
- table: table {{headers[], rows[][]}} — 3–5 строк данных
- diagram: key_points[] (4–6), caption?
- conclusion: takeaways[] (3–5)
- thank_you: subtitle?, contact?

Каждый слайд: "speaker_notes", "image" {{"source":"none|materials|generate", "material_ref", "prompt"}}.

Правила визуального дизайна:
- Первый: title; последний: thank_you или conclusion.
- Числа, %%, ROI, сроки → kpi или results (не текстовые абзацы).
- Этапы/фазы → timeline или process (3–5 шагов с описанием).
- A vs B, до/после → comparison.
- Преимущества/функции → cards (3–4 карточки, в highlight — метрика).
- Связи между блоками → diagram (4–6 key_points).
- Запрещено: bullets[] или title_content как основной контент.
- Не более {max_slides} слайдов. Русский язык.
- cards[].text и пункты — 1–2 ёмких предложения из плана (факты, цифры, примеры).
- cards[].highlight — опционально: «+32%%», «6 мес», «Top-3» (из материалов).
- image.source "generate" — до {max_images} слайдов (diagram, comparison, cards, problem); prompt — сцена без текста на картинке.
"""

SEMANTIC_PLAN_PROMPT = """Ты арт-директор презентаций. По плану определи СЕМАНТИЧЕСКИЙ тип каждого слайда.

Верни ТОЛЬКО JSON:
{{
  "slides": [
    {{
      "type": "title|agenda|problem|goals|kpi|cards|comparison|timeline|process|results|table|diagram|conclusion|thank_you",
      "title": "краткий заголовок",
      "intent": "зачем слайд и какой визуальный формат (KPI-карточки, таймлайн, таблица...)"
    }}
  ]
}}

Правила:
- Первый слайд: type "title".
- Последний: "thank_you" или "conclusion".
- Не используй текстовые «простыни» — выбирай визуальные типы.
- Числа и проценты → kpi или results.
- Этапы/фазы → timeline или process.
- Сравнение «до/после», A vs B → comparison.
- Список преимуществ → cards (не буллеты).
- Повестка → agenda.
- Не более {max_slides} слайдов.
- Текст на русском.
"""

CONTENT_PROMPT = """Ты наполняешь слайды презентации визуально насыщенным JSON.

Типы и поля — как в art-director brief: kpi/results с цифрами, cards с highlight-метриками,
diagram с 4–6 key_points, comparison с двумя колонками, table с реальными строками данных.

Общие поля: "type", "title", "speaker_notes", "image" {{"source":"none|materials|generate", ...}}

До {max_images} слайдов с image.source "generate" (diagram, cards, comparison, problem).
Остальные — "none" или "materials" из списка ref.

Верни ТОЛЬКО JSON: {{"slides": [ ... ]}}
Запрещено: title_content + bullets[] как основной контент.
Текст из плана: факты, цифры, без placeholder «—».
"""


async def plan_semantic_structure(
    *,
    agent_id: str,
    outline: str,
    template_name: Optional[str],
    presentation_prompt: Optional[str],
) -> SemanticPlan:
    template_hint = f"Шаблон: «{template_name}»." if template_name else ""
    user_block = ""
    if presentation_prompt and presentation_prompt.strip():
        user_block = f"Запрос:\n{presentation_prompt.strip()}\n\n"

    logger.info("Семантический план: запрос к ИИ (агент=%s)...", agent_id)
    started = time.perf_counter()
    raw = await chat_with_agent_resilient(
        agent_id,
        [
            ChatMessage(
                role="user",
                content=(
                    f"{SEMANTIC_PLAN_PROMPT.format(max_slides=settings.presentation_max_slides)}\n\n"
                    f"{template_hint}\n{user_block}План:\n{outline}"
                ),
            )
        ],
    )
    logger.info("Семантический план готов за %.1f с", time.perf_counter() - started)
    try:
        payload = extract_json(raw)
        return SemanticPlan.model_validate(payload)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Не удалось построить семантический план: {exc}",
        ) from exc


async def fill_slide_content(
    *,
    agent_id: str,
    outline: str,
    semantic_plan: SemanticPlan,
    available_image_refs: List[str],
    quality_feedback: str = "",
) -> PresentationSlides:
    refs_block = (
        "Доступные material_ref:\n" + "\n".join(f"- {r}" for r in available_image_refs)
        if available_image_refs
        else "Изображений из материалов нет."
    )
    plan_json = json.dumps(
        {"slides": [s.model_dump() for s in semantic_plan.slides]},
        ensure_ascii=False,
        indent=2,
    )
    feedback_block = f"\n\nИсправления:\n{quality_feedback}" if quality_feedback else ""

    logger.info("Контент слайдов: запрос к ИИ (агент=%s)...", agent_id)
    started = time.perf_counter()
    raw = await chat_with_agent_resilient(
        agent_id,
        [
            ChatMessage(
                role="user",
                content=(
                    f"{CONTENT_PROMPT.format(max_images=settings.presentation_max_generated_images)}\n\n"
                    f"{refs_block}\n\n"
                    f"Семантический план:\n{plan_json}\n\n"
                    f"Исходный план:\n{outline}{feedback_block}"
                ),
            )
        ],
    )
    logger.info("Контент слайдов готов за %.1f с", time.perf_counter() - started)
    presentation = _parse_slides_response(raw, semantic_plan)

    if not presentation.slides:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="ИИ вернул пустой список слайдов",
        )
    if len(presentation.slides) > settings.presentation_max_slides:
        presentation.slides = presentation.slides[: settings.presentation_max_slides]
    return presentation


def _semantic_plan_from_slides_raw(slides_raw: List[Dict[str, Any]]) -> SemanticPlan:
    items = []
    for slide in slides_raw:
        slide_type = slide.get("type") or "cards"
        items.append(
            SemanticPlanItem(
                type=slide_type,
                title=str(slide.get("title") or "Слайд"),
                intent=str(slide.get("intent") or slide_type),
            )
        )
    return SemanticPlan(slides=items)


def _validate_presentation_slides(slides: List[Dict[str, Any]]) -> PresentationSlides:
    repaired: List[Dict[str, Any]] = []
    for index, slide in enumerate(slides):
        item = normalize_slide_payload(slide)
        try:
            PresentationSlides.model_validate({"slides": [item]})
            repaired.append(item)
        except Exception as slide_error:
            logger.warning("Слайд %s после нормализации: %s — перевод в cards", index, slide_error)
            item["type"] = "cards"
            item.pop("table", None)
            item = normalize_slide_payload(item)
            repaired.append(item)
    return PresentationSlides.model_validate({"slides": repaired})


def _parse_slides_response(raw: str, semantic_plan: SemanticPlan) -> PresentationSlides:
    try:
        payload = extract_json(raw)
        slides_raw = payload.get("slides") or []
        normalized = _normalize_slides_payload(slides_raw, semantic_plan)
        return _validate_presentation_slides(normalized)
    except Exception as first_error:
        logger.warning("Разбор JSON слайдов, локальная нормализация: %s", first_error)
        try:
            payload = extract_json(raw)
            slides_raw = payload.get("slides") or []
            coerced = _normalize_slides_payload(slides_raw, semantic_plan)
            return _validate_presentation_slides(coerced)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Не удалось разобрать JSON слайдов: {exc}",
            ) from exc


async def plan_slides_unified(
    *,
    agent_id: str,
    outline: str,
    available_image_refs: List[str],
    template_name: Optional[str] = None,
    presentation_prompt: Optional[str] = None,
) -> PresentationSlides:
    template_hint = f"Шаблон: «{template_name}»." if template_name else ""
    user_block = ""
    if presentation_prompt and presentation_prompt.strip():
        user_block = f"Запрос:\n{presentation_prompt.strip()}\n\n"
    refs_block = (
        "Доступные material_ref:\n" + "\n".join(f"- {r}" for r in available_image_refs)
        if available_image_refs
        else "Изображений из материалов нет."
    )

    logger.info(
        "Единый JSON слайдов: запрос к ИИ (агент=%s, до %s слайдов)...",
        agent_id,
        settings.presentation_max_slides,
    )
    started = time.perf_counter()
    raw = await chat_with_agent_resilient(
        agent_id,
        [
            ChatMessage(
                role="user",
                content=(
                    f"{UNIFIED_SLIDES_PROMPT.format(max_slides=settings.presentation_max_slides, max_images=settings.presentation_max_generated_images)}\n\n"
                    f"{template_hint}\n{refs_block}\n{user_block}План:\n{outline}"
                ),
            )
        ],
    )
    logger.info("Единый JSON слайдов готов за %.1f с", time.perf_counter() - started)
    payload = extract_json(raw)
    slides_raw = payload.get("slides") or []
    semantic_plan = _semantic_plan_from_slides_raw(slides_raw)
    return _parse_slides_response(raw, semantic_plan)


def _normalize_slides_payload(
    slides_raw: List[Dict[str, Any]],
    semantic_plan: SemanticPlan,
) -> List[Dict[str, Any]]:
    coerced: List[Dict[str, Any]] = []
    for index, slide in enumerate(slides_raw):
        item = dict(slide)
        if index < len(semantic_plan.slides):
            item.setdefault("type", semantic_plan.slides[index].type)
            item.setdefault("title", semantic_plan.slides[index].title)
        item = coerce_away_bullet_layout(item)
        item = normalize_slide_payload(item)
        coerced.append(item)
    coerced = apply_layout_rules(coerced)
    return [normalize_slide_payload(slide) for slide in coerced]


async def plan_slides_with_quality_loop(
    *,
    agent_id: str,
    outline: str,
    available_image_refs: List[str],
    template_name: Optional[str] = None,
    presentation_prompt: Optional[str] = None,
) -> PresentationSlides:
    pipeline_started = time.perf_counter()
    logger.info("Планирование слайдов: старт (агент=%s)", agent_id)
    try:
        presentation = await plan_slides_unified(
            agent_id=agent_id,
            outline=outline,
            available_image_refs=available_image_refs,
            template_name=template_name,
            presentation_prompt=presentation_prompt,
        )
    except HTTPException as exc:
        if exc.status_code not in (
            status.HTTP_503_SERVICE_UNAVAILABLE,
            status.HTTP_502_BAD_GATEWAY,
        ):
            raise
        logger.warning("Единый запрос слайдов не удался (%s), двухэтапный режим", exc.detail)
        semantic_plan = await plan_semantic_structure(
            agent_id=agent_id,
            outline=outline,
            template_name=template_name,
            presentation_prompt=presentation_prompt,
        )
        presentation = await fill_slide_content(
            agent_id=agent_id,
            outline=outline,
            semantic_plan=semantic_plan,
            available_image_refs=available_image_refs,
        )

    report = score_presentation(presentation)
    if not report.passes:
        logger.info(
            "Качество %.3f < %.2f — локальная донастройка типов (без повторного LLM)",
            report.average_score,
            QUALITY_THRESHOLD,
        )
        semantic_plan = _semantic_plan_from_slides_raw(
            [slide.model_dump() for slide in presentation.slides]
        )
        presentation = _merge_plan_types(presentation, semantic_plan)

    logger.info(
        "Планирование слайдов: готово, %s слайдов за %.1f с",
        len(presentation.slides),
        time.perf_counter() - pipeline_started,
    )
    return presentation


def _merge_plan_types(
    presentation: PresentationSlides,
    semantic_plan: SemanticPlan,
) -> PresentationSlides:
    merged: List[Dict[str, Any]] = []
    for index, slide in enumerate(presentation.slides):
        data = slide.model_dump()
        if index < len(semantic_plan.slides):
            data["type"] = semantic_plan.slides[index].type
        merged.append(coerce_away_bullet_layout(data))
    merged = apply_layout_rules(merged)
    return PresentationSlides.model_validate(
        {"slides": [normalize_slide_payload(slide) for slide in merged]}
    )
