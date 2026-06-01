from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Iterable, List

from app.schemas.semantic_slides import (
    AgendaSlide,
    CardItem,
    CardsSlide,
    ComparisonSlide,
    ConclusionSlide,
    DiagramSlide,
    GoalsSlide,
    KpiSlide,
    PresentationSlides,
    ProblemSlide,
    ProcessSlide,
    ResultsSlide,
    SemanticSlide,
    TableSlide,
    ThankYouSlide,
    TimelineSlide,
    TitleSlide,
)
from app.services.slide_content_density import normalize_content_text
from app.services.slide_text_limits import (
    MAX_BODY_CHARS,
    MAX_SUBTITLE_CHARS,
    MAX_TITLE_CHARS,
    clamp_text,
)

logger = logging.getLogger(__name__)

_MULTISPACE_RE = re.compile(r"\s+")
_MIN_SLIDE_TEXT_LEN = 24


@dataclass
class TextControlIssue:
    level: str
    message: str


@dataclass
class SlideTextControlReport:
    slide_index: int
    slide_type: str
    title: str
    issues: List[TextControlIssue] = field(default_factory=list)

    @property
    def has_warnings(self) -> bool:
        return any(item.level in ("warning", "error") for item in self.issues)


def _clean_text(value: str, *, fallback: str = "") -> str:
    compact = _MULTISPACE_RE.sub(" ", (value or "").strip())
    return compact or fallback


def _trim_title(value: str) -> str:
    return clamp_text(_clean_text(value), MAX_TITLE_CHARS)


def _trim_body(value: str) -> str:
    return clamp_text(_clean_text(value), MAX_BODY_CHARS)


def _trim_subtitle(value: str) -> str:
    return clamp_text(_clean_text(value), MAX_SUBTITLE_CHARS)


def _dedupe_keep_order(items: Iterable[str]) -> List[str]:
    result: List[str] = []
    seen = set()
    for raw in items:
        text = _clean_text(str(raw))
        if not text:
            continue
        key = text.casefold()
        if key in seen:
            continue
        seen.add(key)
        result.append(text)
    return result


def _flatten_slide_texts(slide: SemanticSlide) -> List[str]:
    texts: List[str] = [slide.title]
    if isinstance(slide, TitleSlide):
        texts.extend([slide.subtitle or ""])
    elif isinstance(slide, AgendaSlide):
        texts.extend(slide.items)
    elif isinstance(slide, ProblemSlide):
        texts.extend(slide.pain_points)
    elif isinstance(slide, GoalsSlide):
        texts.extend(slide.goals)
    elif isinstance(slide, KpiSlide):
        for metric in slide.metrics:
            texts.extend([metric.label, metric.value, metric.note or ""])
    elif isinstance(slide, CardsSlide):
        for card in slide.cards:
            texts.extend([card.title, card.text, card.highlight or ""])
    elif isinstance(slide, ComparisonSlide):
        texts.extend([slide.left.heading, slide.right.heading, *slide.left.points, *slide.right.points])
    elif isinstance(slide, TimelineSlide):
        for step in slide.steps:
            texts.extend([step.label, step.description or ""])
    elif isinstance(slide, ProcessSlide):
        for step in slide.steps:
            texts.extend([step.title, step.description or ""])
    elif isinstance(slide, ResultsSlide):
        texts.extend([slide.summary or ""])
        for item in slide.results:
            texts.extend([item.label, item.value])
    elif isinstance(slide, TableSlide):
        texts.extend(slide.table.headers)
        for row in slide.table.rows:
            texts.extend(row)
    elif isinstance(slide, DiagramSlide):
        texts.extend([slide.caption or "", *slide.key_points])
    elif isinstance(slide, ConclusionSlide):
        texts.extend(slide.takeaways)
    elif isinstance(slide, ThankYouSlide):
        texts.extend([slide.subtitle or "", slide.contact or ""])
    return [item for item in (_clean_text(t) for t in texts) if item]


def enforce_slide_text_control(slide: SemanticSlide, *, slide_index: int) -> SlideTextControlReport:
    """
    Нормализация текста перед рендером.
    ИИ-агент (semantic_slide_planner / blueprint LLM) лимит символов на поле не задаёт;
    обрезка здесь — только санитизация и защита от экстремально длинных строк.
    """
    report = SlideTextControlReport(
        slide_index=slide_index,
        slide_type=slide.type,
        title=slide.title,
    )
    truncated_any = False

    def body_field(value: str, *, fallback: str = "") -> str:
        nonlocal truncated_any
        raw = _clean_text(value, fallback=fallback)
        raw = normalize_content_text(raw) or fallback
        out = _trim_body(raw) if raw else fallback
        if raw and len(raw) > MAX_BODY_CHARS:
            truncated_any = True
        return out or fallback

    slide.title = _trim_title(_clean_text(slide.title, fallback=f"Слайд {slide_index + 1}"))
    if len(slide.title) < 3:
        slide.title = f"Слайд {slide_index + 1}"
        report.issues.append(TextControlIssue("warning", "заголовок заменен на безопасный fallback"))

    if isinstance(slide, TitleSlide):
        slide.subtitle = _trim_subtitle(slide.subtitle or "") or None
    elif isinstance(slide, AgendaSlide):
        slide.items = [body_field(i) for i in _dedupe_keep_order(slide.items)[:8]] or ["План"]
    elif isinstance(slide, ProblemSlide):
        slide.pain_points = [body_field(p) for p in _dedupe_keep_order(slide.pain_points)[:5]] or [
            "Проблема уточняется"
        ]
    elif isinstance(slide, GoalsSlide):
        slide.goals = [body_field(g) for g in _dedupe_keep_order(slide.goals)[:5]] or ["Цель уточняется"]
    elif isinstance(slide, KpiSlide):
        for metric in slide.metrics:
            metric.label = body_field(metric.label, fallback="Показатель")
            metric.value = body_field(metric.value, fallback="—")
            metric.note = body_field(metric.note or "") or None
    elif isinstance(slide, CardsSlide):
        for idx, card in enumerate(slide.cards, start=1):
            card.title = _trim_title(_clean_text(card.title, fallback=f"Пункт {idx}"))
            card.text = body_field(card.text, fallback="—")
            card.highlight = body_field(card.highlight or "") or None
        while len(slide.cards) < 2:
            slide.cards.append(
                CardItem(title=f"Пункт {len(slide.cards) + 1}", text=slide.title or "—")
            )
    elif isinstance(slide, ComparisonSlide):
        slide.left.heading = _trim_title(_clean_text(slide.left.heading, fallback="Вариант A"))
        slide.right.heading = _trim_title(_clean_text(slide.right.heading, fallback="Вариант B"))
        slide.left.points = [body_field(p) for p in _dedupe_keep_order(slide.left.points)[:5]] or ["—"]
        slide.right.points = [body_field(p) for p in _dedupe_keep_order(slide.right.points)[:5]] or ["—"]
    elif isinstance(slide, TimelineSlide):
        for idx, step in enumerate(slide.steps, start=1):
            step.label = _trim_title(_clean_text(step.label, fallback=f"Шаг {idx}"))
            step.description = body_field(step.description or "") or None
    elif isinstance(slide, ProcessSlide):
        for idx, step in enumerate(slide.steps, start=1):
            step.title = _trim_title(_clean_text(step.title, fallback=f"Шаг {idx}"))
            step.description = body_field(step.description or "") or None
    elif isinstance(slide, ResultsSlide):
        slide.summary = _trim_subtitle(slide.summary or "") or None
        for idx, result in enumerate(slide.results, start=1):
            result.label = body_field(result.label, fallback=f"Итог {idx}")
            result.value = body_field(result.value, fallback="—")
    elif isinstance(slide, TableSlide):
        slide.table.headers = [_trim_title(h) for h in _dedupe_keep_order(slide.table.headers)[:6]] or [
            "Показатель",
            "Значение",
        ]
        normalized_rows: List[List[str]] = []
        for row in slide.table.rows[:8]:
            cleaned_row = [body_field(cell) for cell in row[: len(slide.table.headers)]]
            cleaned_row = [cell for cell in cleaned_row if cell]
            if cleaned_row:
                normalized_rows.append(cleaned_row)
        slide.table.rows = normalized_rows or [["—"] * len(slide.table.headers)]
    elif isinstance(slide, DiagramSlide):
        slide.caption = _trim_subtitle(slide.caption or "") or None
        slide.key_points = [body_field(p) for p in _dedupe_keep_order(slide.key_points)[:4]] or [
            "Ключевая мысль"
        ]
    elif isinstance(slide, ConclusionSlide):
        slide.takeaways = [body_field(t) for t in _dedupe_keep_order(slide.takeaways)[:5]] or ["Итог"]
    elif isinstance(slide, ThankYouSlide):
        slide.subtitle = _trim_subtitle(slide.subtitle or "") or None
        slide.contact = body_field(slide.contact or "") or None

    flat_texts = _flatten_slide_texts(slide)
    total_len = sum(len(item) for item in flat_texts)
    unique_count = len({item.casefold() for item in flat_texts})
    if total_len < _MIN_SLIDE_TEXT_LEN:
        report.issues.append(TextControlIssue("warning", "слишком мало текстового содержания"))
    if flat_texts and unique_count <= max(1, len(flat_texts) // 2):
        report.issues.append(TextControlIssue("warning", "много повторяющихся фрагментов текста"))
    if truncated_any:
        report.issues.append(
            TextControlIssue("info", f"часть полей сокращена свыше {MAX_BODY_CHARS} символов")
        )
    return report


def enforce_presentation_text_control(slides: PresentationSlides) -> List[SlideTextControlReport]:
    reports: List[SlideTextControlReport] = []
    for index, slide in enumerate(slides.slides):
        report = enforce_slide_text_control(slide, slide_index=index)
        reports.append(report)
        if report.has_warnings:
            messages = "; ".join(f"{it.level}: {it.message}" for it in report.issues)
            logger.warning(
                "Текст-контроль слайд %s (%s): %s",
                index + 1,
                slide.type,
                messages,
            )
    warned = sum(1 for report in reports if report.has_warnings)
    logger.info(
        "Текст-контроль презентации: слайдов=%s, с предупреждениями=%s",
        len(reports),
        warned,
    )
    return reports
