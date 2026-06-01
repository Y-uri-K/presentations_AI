from __future__ import annotations

import re
from typing import List

from app.schemas.semantic_slides import (
    AgendaSlide,
    CardsSlide,
    ComparisonSlide,
    ConclusionSlide,
    DiagramSlide,
    GoalsSlide,
    KpiSlide,
    PresentationSlides,
    ProblemSlide,
    ProcessSlide,
    SemanticSlide,
    TimelineSlide,
)
from app.services.presentation_gamma.outline import parse_outline_chunks

_MULTISPACE = re.compile(r"\s+")
_PLACEHOLDER_ONLY = frozenset({"—", "-", "–", "•", "...", "…", "n/a", "na"})


def normalize_content_text(text: str) -> str:
    """Только очистка; без искусственных дописок."""
    cleaned = _MULTISPACE.sub(" ", (text or "").strip())
    if not cleaned:
        return ""
    if cleaned.casefold() in _PLACEHOLDER_ONLY:
        return ""
    return cleaned


def prefer_richer_text(current: str, outline: str) -> str:
    """Берёт более полный текст из плана, если блок слайда слишком короткий."""
    cur = normalize_content_text(current)
    out = normalize_content_text(outline)
    if not out:
        return cur
    if not cur:
        return out
    if len(out) > len(cur) + 30 or (len(cur) < 40 and len(out) >= len(cur)):
        return out
    return cur


def short_heading_from_body(body: str, *, max_words: int = 8) -> str:
    words = normalize_content_text(body).split()
    if not words:
        return "Пункт"
    return " ".join(words[:max_words])


def _bullets_from_chunk(chunk: str) -> List[str]:
    lines: List[str] = []
    for line in chunk.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        item = re.match(r"^(?:[-*•]|\d+[.)])\s+(.+)$", line)
        if item:
            lines.append(item.group(1).strip())
        elif line:
            lines.append(line)
    return [normalize_content_text(x) for x in lines if normalize_content_text(x)]


def _pick_source(index: int, sources: List[str], fallback: str) -> str:
    if not sources:
        return normalize_content_text(fallback)
    if index < len(sources):
        return sources[index]
    if len(sources) == 1:
        return sources[0]
    return sources[min(index, len(sources) - 1)]


def _enrich_slide(slide: SemanticSlide, outline_bullets: List[str]) -> None:
    if isinstance(slide, CardsSlide):
        for idx, card in enumerate(slide.cards):
            raw = normalize_content_text(card.text or card.title or "")
            body = prefer_richer_text(raw, _pick_source(idx, outline_bullets, raw))
            if body:
                card.text = body
                card.title = short_heading_from_body(body)
    elif isinstance(slide, AgendaSlide):
        slide.items = [
            prefer_richer_text(item, _pick_source(i, outline_bullets, item))
            for i, item in enumerate(slide.items[:5])
        ]
        slide.items = [x for x in slide.items if x] or slide.items
    elif isinstance(slide, ProblemSlide):
        slide.pain_points = [
            prefer_richer_text(p, _pick_source(i, outline_bullets, p))
            for i, p in enumerate(slide.pain_points[:5])
        ]
        slide.pain_points = [x for x in slide.pain_points if x] or slide.pain_points
    elif isinstance(slide, GoalsSlide):
        slide.goals = [
            prefer_richer_text(g, _pick_source(i, outline_bullets, g))
            for i, g in enumerate(slide.goals[:5])
        ]
        slide.goals = [x for x in slide.goals if x] or slide.goals
    elif isinstance(slide, ComparisonSlide):
        for i, point in enumerate(slide.left.points):
            slide.left.points[i] = normalize_content_text(point) or point
        for i, point in enumerate(slide.right.points):
            slide.right.points[i] = normalize_content_text(point) or point
    elif isinstance(slide, TimelineSlide):
        for idx, step in enumerate(slide.steps):
            desc = prefer_richer_text(
                step.description or "",
                _pick_source(idx, outline_bullets, step.label or ""),
            )
            if desc:
                step.description = desc
    elif isinstance(slide, ProcessSlide):
        for idx, step in enumerate(slide.steps):
            desc = prefer_richer_text(
                step.description or "",
                _pick_source(idx, outline_bullets, step.title or ""),
            )
            if desc:
                step.description = desc
    elif isinstance(slide, DiagramSlide):
        slide.key_points = [
            prefer_richer_text(p, _pick_source(i, outline_bullets, p))
            for i, p in enumerate(slide.key_points[:4])
        ]
        slide.key_points = [x for x in slide.key_points if x] or slide.key_points
    elif isinstance(slide, ConclusionSlide):
        slide.takeaways = [
            prefer_richer_text(t, _pick_source(i, outline_bullets, t))
            for i, t in enumerate(slide.takeaways[:5])
        ]
        slide.takeaways = [x for x in slide.takeaways if x] or slide.takeaways


def enrich_presentation_from_outline(
    slides: PresentationSlides,
    outline: str,
    *,
    max_items_per_slide: int = 3,
) -> None:
    """Подставляет из плана более полные формулировки; без шаблонных фраз."""
    chunks = parse_outline_chunks(outline)
    for index, slide in enumerate(slides.slides):
        bullets = _bullets_from_chunk(chunks[index]) if index < len(chunks) else []
        _enrich_slide(slide, bullets)
        _cap_slide_items(slide, max_items=max_items_per_slide)


def _cap_slide_items(slide: SemanticSlide, *, max_items: int) -> None:
    if isinstance(slide, CardsSlide) and len(slide.cards) > max_items:
        slide.cards = slide.cards[:max_items]
    elif isinstance(slide, AgendaSlide) and len(slide.items) > max_items:
        slide.items = slide.items[:max_items]
    elif isinstance(slide, ProblemSlide) and len(slide.pain_points) > max_items:
        slide.pain_points = slide.pain_points[:max_items]
    elif isinstance(slide, DiagramSlide) and len(slide.key_points) > max_items:
        slide.key_points = slide.key_points[:max_items]
