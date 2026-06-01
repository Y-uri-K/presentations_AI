from __future__ import annotations

import re
from typing import List

from app.schemas.slides import SlideImageSpec
from app.schemas.template_blueprint import (
    BlueprintCard,
    BlueprintSlide,
    PresentationBlueprint,
    TemplateCatalog,
)
from app.services.analytics_outline import build_analytics_blueprint_slide, detect_analytics_kind
from app.services.presentation_gamma.outline import parse_outline_chunks
from app.services.slide_text_limits import MAX_SUBTITLE_CHARS, card_title_from_text
from app.services.template_driven.layout_matcher import _outline_topic_type, assign_template_layouts


def _bullets_from_chunk(chunk: str) -> List[str]:
    lines = []
    for line in chunk.splitlines():
        line = line.strip()
        if not line:
            continue
        bullet = re.match(r"^#{1,2}\s+(.+)$", line)
        if bullet:
            continue
        item = re.match(r"^(?:[-*•]|\d+[.)])\s+(.+)$", line)
        if item:
            lines.append(item.group(1).strip())
        elif line and not line.startswith("#"):
            lines.append(line)
    return lines


def _title_from_chunk(chunk: str, fallback: str) -> str:
    for line in chunk.splitlines():
        match = re.match(r"^#{1,2}\s+(.+)$", line.strip())
        if match:
            return match.group(1).strip()
    return fallback


def blueprint_from_outline(
    *,
    outline: str,
    title: str,
    catalog: TemplateCatalog,
) -> PresentationBlueprint:
    """Быстрый blueprint из плана без LLM — запасной путь при таймауте ИИ."""
    chunks = parse_outline_chunks(outline)
    slides: List[BlueprintSlide] = []

    for index, chunk in enumerate(chunks):
        topic_title = _title_from_chunk(chunk, f"Тема {index + 1}")
        bullets = _bullets_from_chunk(chunk)
        slide_type = _outline_topic_type(topic_title)
        lowered = topic_title.lower()
        if slide_type == "title_content" and any(
            w in lowered for w in ("схем", "диаграм", "архитект", "модел", "график", "процесс")
        ):
            slide_type = "diagram"

        if index == 0:
            slide_type = "title"
            slides.append(
                BlueprintSlide(
                    slide_type="title",
                    template_key="",
                    topic=topic_title,
                    title=title if index == 0 else topic_title,
                    subtitle="\n".join(bullets)[:MAX_SUBTITLE_CHARS] if bullets else topic_title,
                    bullets=bullets,
                    image=SlideImageSpec(source="none"),
                )
            )
            continue
        body = "\n".join(bullets) if bullets else f"Развёрнутое содержание раздела «{topic_title}»."

        if index == len(chunks) - 1 and len(chunks) > 1:
            takeaway_items = bullets or [body]
            while len(takeaway_items) < 2:
                takeaway_items.append(f"Итог {len(takeaway_items) + 1}: {topic_title}")
            slides.append(
                BlueprintSlide(
                    slide_type="conclusion",
                    template_key="",
                    topic=topic_title,
                    title=topic_title,
                    subtitle=body[:MAX_SUBTITLE_CHARS],
                    bullets=takeaway_items[:5],
                    image=SlideImageSpec(source="none"),
                )
            )
            continue

        analytics_kind = detect_analytics_kind(chunk, bullets)
        if analytics_kind:
            slides.append(
                build_analytics_blueprint_slide(
                    kind=analytics_kind,
                    topic_title=topic_title,
                    bullets=bullets,
                    body=body,
                )
            )
            continue

        if slide_type == "cards" or len(bullets) >= 3:
            card_items = bullets[:6] if bullets else [topic_title, f"Ключевые идеи раздела «{topic_title}»"]
            while len(card_items) < 2:
                card_items.append(f"Аспект {len(card_items) + 1}: {topic_title}")
            cards = [
                BlueprintCard(
                    title=card_title_from_text(text, index=card_index),
                    text=text,
                )
                for card_index, text in enumerate(card_items[:6], start=1)
            ]
            slides.append(
                BlueprintSlide(
                    slide_type="cards",
                    template_key="",
                    topic=topic_title,
                    title=topic_title,
                    cards=cards,
                    image=SlideImageSpec(source="none"),
                )
            )
            continue

        slides.append(
            BlueprintSlide(
                slide_type="title_content",  # type: ignore[arg-type]
                template_key="",
                topic=topic_title,
                title=topic_title,
                subtitle=body[:MAX_SUBTITLE_CHARS],
                bullets=bullets or [body],
                image=SlideImageSpec(source="none"),
            )
        )

    blueprint = PresentationBlueprint(title=title, slides=slides[:10])
    assign_template_layouts(blueprint, catalog)
    return blueprint
