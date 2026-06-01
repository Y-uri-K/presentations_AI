from __future__ import annotations

import logging

from app.config import get_settings
from app.schemas.slides import PresentationSlides, SlideImageSpec

logger = logging.getLogger(__name__)
settings = get_settings()

_VISUAL_TYPES = frozenset(
    {"diagram", "comparison", "process", "timeline", "cards", "kpi", "table"}
)

def _safe_str(value: object) -> str:
    return str(value).strip() if value is not None else ""


def _slide_keywords(slide: object, *, max_items: int = 8) -> list[str]:
    """Ключевые слова по содержанию слайда — чтобы картинка была по теме."""
    items: list[str] = []
    slide_type = _safe_str(getattr(slide, "type", ""))

    def add(text: object) -> None:
        t = _safe_str(text)
        if not t:
            return
        items.append(t)

    if slide_type == "cards":
        for card in (getattr(slide, "cards", None) or [])[:max_items]:
            add(getattr(card, "title", None))
            add(getattr(card, "text", None))
    elif slide_type == "kpi":
        for metric in (getattr(slide, "metrics", None) or [])[:max_items]:
            add(getattr(metric, "label", None))
            add(getattr(metric, "value", None))
    elif slide_type == "comparison":
        left = getattr(slide, "left", None)
        right = getattr(slide, "right", None)
        add(getattr(left, "heading", None))
        add(getattr(right, "heading", None))
        for p in (getattr(left, "points", None) or [])[:5]:
            add(p)
        for p in (getattr(right, "points", None) or [])[:5]:
            add(p)
    elif slide_type in ("timeline", "process"):
        for step in (getattr(slide, "steps", None) or [])[:max_items]:
            add(getattr(step, "label", None) or getattr(step, "title", None))
            add(getattr(step, "description", None))
    elif slide_type == "table":
        table = getattr(slide, "table", None)
        for h in (getattr(table, "headers", None) or [])[:6]:
            add(h)
    elif slide_type == "diagram":
        add(getattr(slide, "caption", None))
        for p in (getattr(slide, "key_points", None) or [])[:4]:
            add(p)

    # глобально: заголовок в начале
    title = _safe_str(getattr(slide, "title", "")) or _safe_str(getattr(slide, "topic", ""))
    cleaned = [title] + items
    # дедуп (case-insensitive), ограничение
    seen = set()
    result: list[str] = []
    for t in cleaned:
        key = t.casefold()
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(t)
        if len(result) >= max_items:
            break
    return result


def clear_generated_image_requests(slides: PresentationSlides) -> None:
    """Убирает запросы на AI-иллюстрации (оставляет materials)."""
    for slide in slides.slides:
        if slide.image.source == "generate":
            slide.image = SlideImageSpec(source="none")


def apply_slide_image_plan(
    slides: PresentationSlides,
    *,
    presentation_prompt: str | None = None,
    content_image_side: str = "right",
    enabled: bool = True,
) -> None:
    """Назначает до N слайдов с image.source=generate (Polza)."""
    if not enabled:
        clear_generated_image_requests(slides)
        return
    limit = settings.presentation_max_generated_images
    if limit <= 0:
        return

    scored: list[tuple[int, int]] = []
    for index, slide in enumerate(slides.slides):
        if slide.type in ("title", "thank_you", "table"):
            continue
        score = 0
        if slide.type == "diagram":
            score += 100
        elif slide.type == "kpi":
            score += 70
        elif slide.type == "results":
            score += 55
        elif slide.type in ("comparison", "process", "timeline"):
            score += 60
        elif slide.type == "cards":
            score += 30
        elif slide.type in _VISUAL_TYPES:
            score += 10
        if index >= len(slides.slides) - 2:
            score -= 80
        elif 0 < index < len(slides.slides) - 1:
            score += 5
        scored.append((score, index))

    scored.sort(key=lambda item: item[0], reverse=True)
    chosen = [index for score, index in scored[:limit] if score > 0]
    if not chosen and scored:
        chosen = [scored[0][1]]

    for index in chosen:
        slide = slides.slides[index]
        context = (presentation_prompt or "").strip()[:240]
        keywords = _slide_keywords(slide)
        kw_line = "; ".join(keywords[:8])
        prompt = (
            "Abstract visual illustration on white background. "
            "STRICTLY NO text, letters, numbers, words, labels or captions on the image. "
            "No logos, no people. Icons and shapes only. "
            f"Topic: {kw_line}."
        )
        if context:
            prompt += f" Presentation context: {context}."
        if slide.type == "diagram":
            placement = "left"
        elif slide.type in ("comparison", "timeline", "process"):
            placement = "vertical"
        elif slide.type in ("kpi", "results"):
            placement = "right"
        else:
            placement = content_image_side if content_image_side in ("left", "right") else "right"
        slide.image = SlideImageSpec(
            source="generate",
            prompt=prompt,
            placement=placement,
        )

    if chosen:
        logger.info(
            "План изображений: generate на слайдах %s (лимит %s)",
            [i + 1 for i in chosen],
            limit,
        )
