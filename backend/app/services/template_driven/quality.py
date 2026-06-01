from __future__ import annotations

from typing import Optional

from app.schemas.template_blueprint import BlueprintSlide, SlideQualityScores, TemplateSlideSchema
from app.services.template_driven.text_utils import is_placeholder_text, word_count


def score_blueprint_slide(
    slide: BlueprintSlide,
    template: Optional[TemplateSlideSchema],
) -> SlideQualityScores:
    required_slots = len(template.required_fields) if template else 2
    filled_slots = sum(
        1 for value in slide.slot_texts.values() if value and not is_placeholder_text(value)
    )
    if slide.title and not is_placeholder_text(slide.title):
        filled_slots += 1
    if slide.subtitle and not is_placeholder_text(slide.subtitle):
        filled_slots += 1

    template_coverage = min(1.0, filled_slots / max(required_slots, 1))

    text_parts = [slide.title, slide.subtitle or ""]
    text_parts.extend(slide.slot_texts.values())
    for card in slide.cards:
        text_parts.extend([card.title, card.text])
    if slide.comparison:
        text_parts.extend(slide.comparison.left_points)
        text_parts.extend(slide.comparison.right_points)
    if slide.table:
        for row in slide.table.rows:
            text_parts.extend(row)

    words = sum(word_count(part) for part in text_parts if part)
    information_density = min(1.0, words / 80.0)

    visual_fields = 0
    visual_filled = 0
    if slide.cards:
        visual_fields += len(slide.cards)
        visual_filled += sum(1 for c in slide.cards if word_count(c.text) >= 15)
    if slide.metrics:
        visual_fields += len(slide.metrics)
        visual_filled += len(slide.metrics)
    if slide.table and slide.table.rows:
        visual_fields += 1
        visual_filled += 1
    visual_completeness = visual_filled / visual_fields if visual_fields else min(1.0, information_density)

    content_completeness = 0.0
    checks = 0
    if slide.title:
        checks += 1
        content_completeness += 1.0 if word_count(slide.title) >= 5 else 0.4
    if slide.slide_type == "cards" and slide.cards:
        checks += len(slide.cards)
        content_completeness += sum(
            1.0 if word_count(c.text) >= 20 else 0.3 for c in slide.cards
        )
    elif slide.bullets:
        checks += len(slide.bullets)
        content_completeness += sum(1.0 if word_count(b) >= 8 else 0.3 for b in slide.bullets)
    else:
        checks += 1
        content_completeness += min(1.0, words / 40.0)

    if checks:
        content_completeness /= checks
    else:
        content_completeness = min(1.0, words / 30.0)

    return SlideQualityScores(
        content_completeness=min(1.0, content_completeness),
        visual_completeness=min(1.0, visual_completeness),
        template_coverage=template_coverage,
        information_density=information_density,
    )
