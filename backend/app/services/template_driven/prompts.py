from __future__ import annotations

import json

from app.config import get_settings

settings = get_settings()


def blueprint_phase1_prompt(
    *,
    title: str,
    outline: str,
    catalog_json: str,
    presentation_prompt: str | None,
) -> str:
    n = settings.presentation_max_slides
    return f"""Ты архитектор презентаций. Этап 1: Presentation Blueprint (JSON).

Название: {title}
Запрос: {presentation_prompt or "—"}
План (темы слайдов):
{outline}

Доступные макеты шаблона (источник истины — заполняй ВСЕ слоты):
{catalog_json}

Задача:
1. Для каждой темы плана (макс. {n} слайдов) выбери slide_type и template_key из каталога.
2. Извлеки сущности темы: определения, преимущества, недостатки, примеры, этапы, сравнения, метрики.
3. Распредели сущности по полям макета (cards, columns, table, metrics, timeline_steps…).
4. Не используй один slide_type более 2 раз подряд.
5. Запрещены placeholder-тексты: «Пункт 1», «Введите текст», «ЗАГ», «-», пустые строки.

Верни ТОЛЬКО JSON:
{{
  "title": "...",
  "slides": [
    {{
      "slide_type": "cards",
      "template_key": "из каталога",
      "topic": "тема из плана",
      "title": "заголовок слайда (мин. 5 слов)",
      "subtitle": null,
      "cards": [{{"title": "короткий заголовок до 8 слов", "text": "минимум 2 полных предложения, 40-90 слов"}}],
      "bullets": [],
      "metrics": [],
      "timeline_steps": [],
      "table": null,
      "comparison": null,
      "entities": {{"definitions": [], "advantages": [], "examples": []}},
      "image": {{"source": "none"}}
    }}
  ]
}}

Первый слайд: type=title. Последний: conclusion или title_content с выводами.
Для сравнения — comparison с 3-5 пунктами в каждой колонке.
"""


def blueprint_phase2_prompt(
    *,
    blueprint_json: str,
    catalog_json: str,
    issues: str,
) -> str:
    return f"""Этап 2: дополни и исправь Presentation Blueprint для заполнения PPTX.

Каталог макетов:
{catalog_json}

Текущий blueprint:
{blueprint_json}

Ошибки валидации:
{issues or "нет"}

Требования:
- Каждый content slot и карточка — осмысленный русский текст.
- title: мин. 5 слов; каждая карточка/пункт: минимум 2 полных предложения (40-90 слов); не обрывки фраз.
- Заполни slot_texts: ключ = slot_id из каталога для выбранного template_key, значение = текст.
- Убери placeholder-тексты.
- Сохрани slide_type, template_key, структуру полей.

Верни ТОЛЬКО исправленный JSON того же формата (title + slides)."""


def single_slide_regen_prompt(
    *,
    slide_json: str,
    template_json: str,
    topic: str,
    issues: str,
) -> str:
    return f"""Перегенерируй один слайд презентации.

Тема: {topic}
Макет шаблона: {template_json}
Текущий слайд: {slide_json}
Проблемы: {issues}

Верни ТОЛЬКО JSON одного объекта слайда (как элемент slides[]), полностью заполненный."""
