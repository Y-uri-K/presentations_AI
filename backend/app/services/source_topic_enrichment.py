from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import List, Optional, Tuple

from app.ai.registry import chat_with_agent_resilient
from app.ai.types import ChatMessage
from app.config import get_settings
from app.services.ai_json import extract_json
from app.services.outline_limits import truncate_outline
from app.services.presentation_gamma.outline import extract_presentation_title, strip_title_tag
from app.services.source_file_parser import extract_source_text

logger = logging.getLogger(__name__)
settings = get_settings()

_MAX_SOURCE_CHARS = 14_000
_MAX_OUTLINE_CHARS = 8_000

SOURCE_ENRICHMENT_PROMPT = """Ты аналитик и арт-директор презентаций. Изучи план и исходные материалы.

1) Сформулируй 3–5 ключевых вопросов по теме (что аудитории важно понять).
2) Ответь на каждый вопрос, опираясь ТОЛЬКО на материалы и план (если данных нет — пометь «уточнить»).
3) Извлеки факты для визуальных слайдов: цифры, %%, даты, сравнения, этапы, риски, выводы.
4) Дополни план слайдов: к каждой теме добавь 2–4 конкретных тезиса для карточек/KPI/таблиц.

Верни ТОЛЬКО JSON:
{{
  "questions": ["вопрос 1", ...],
  "answers": ["ответ 1", ...],
  "visual_facts": ["факт с цифрой или сравнением", ...],
  "enriched_outline": "<TITLE>Название</TITLE>\\n\\n# Тема\\n- пункт..."
}}

Правила enriched_outline:
- Сохрани структуру исходного плана (# заголовки слайдов).
- Расширь пункты: полные предложения, цифры, примеры из материалов.
- Не более {max_slides} слайдов-тем.
- Язык: русский.
- Не выдумывай цифры — только из материалов или общие формулировки без fake stats.
"""


@dataclass(frozen=True)
class SourceEnrichmentResult:
    outline: str
    questions: List[str]
    visual_facts: List[str]
    used_agent: bool


def _load_source_blocks(sources: List[Tuple[str, bytes]]) -> List[str]:
    blocks: List[str] = []
    total = 0
    for filename, content in sources:
        try:
            text = extract_source_text(filename=filename, content=content)
        except Exception:
            continue
        text = text.strip()
        if not text:
            continue
        block = f"### {filename}\n{text}"
        if total + len(block) > _MAX_SOURCE_CHARS:
            remain = _MAX_SOURCE_CHARS - total
            if remain > 200:
                blocks.append(block[:remain] + "\n…")
            break
        blocks.append(block)
        total += len(block)
    return blocks


def _merge_outlines(original: str, enriched_body: str) -> str:
    title = extract_presentation_title(original, fallback="Презентация")
    body = strip_title_tag(enriched_body).strip() or strip_title_tag(original).strip()
    body = truncate_outline(body)
    return f"<TITLE>{title}</TITLE>\n\n{body}".strip()


async def enrich_outline_from_sources(
    *,
    agent_id: str,
    outline: str,
    sources: List[Tuple[str, bytes]],
    presentation_prompt: Optional[str] = None,
) -> SourceEnrichmentResult:
    """
    Агент задаёт вопросы по теме, отвечает на них из материалов и расширяет план.
    Без материалов возвращает исходный outline без вызова LLM.
    """
    source_blocks = _load_source_blocks(sources)
    if not source_blocks or not settings.presentation_source_enrichment:
        return SourceEnrichmentResult(
            outline=outline,
            questions=[],
            visual_facts=[],
            used_agent=False,
        )

    prompt_block = ""
    if presentation_prompt and presentation_prompt.strip():
        prompt_block = f"Запрос пользователя:\n{presentation_prompt.strip()}\n\n"

    outline_trimmed = outline[:_MAX_OUTLINE_CHARS]
    materials = "\n\n".join(source_blocks)

    logger.info(
        "Обогащение из источников: агент=%s, файлов=%s, символов материалов≈%s",
        agent_id,
        len(source_blocks),
        len(materials),
    )
    started = time.perf_counter()
    raw = await chat_with_agent_resilient(
        agent_id,
        [
            ChatMessage(
                role="user",
                content=(
                    f"{SOURCE_ENRICHMENT_PROMPT.format(max_slides=settings.presentation_max_slides)}\n\n"
                    f"{prompt_block}"
                    f"Текущий план:\n{outline_trimmed}\n\n"
                    f"Исходные материалы:\n{materials}"
                ),
            )
        ],
    )
    logger.info("Обогащение из источников: готово за %.1f с", time.perf_counter() - started)

    try:
        payload = extract_json(raw)
        enriched = (payload.get("enriched_outline") or "").strip()
        questions = [str(q).strip() for q in (payload.get("questions") or []) if str(q).strip()]
        visual_facts = [str(f).strip() for f in (payload.get("visual_facts") or []) if str(f).strip()]
        if enriched:
            merged = _merge_outlines(outline, enriched)
            if questions:
                logger.info("Вопросы по теме (%s): %s", len(questions), "; ".join(questions[:3]))
            if visual_facts:
                logger.info("Визуальные факты: %s", "; ".join(visual_facts[:4]))
            return SourceEnrichmentResult(
                outline=merged,
                questions=questions,
                visual_facts=visual_facts,
                used_agent=True,
            )
    except Exception as exc:
        logger.warning("Не удалось разобрать обогащение источников: %s", exc)

    return SourceEnrichmentResult(
        outline=outline,
        questions=[],
        visual_facts=[],
        used_agent=False,
    )
