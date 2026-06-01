from __future__ import annotations

from app.schemas.semantic_slides import (
    CardItem,
    CardsSlide,
    ComparisonSide,
    ComparisonSlide,
    ConclusionSlide,
    DiagramSlide,
    KpiSlide,
    MetricItem,
    PresentationSlides,
    ProcessSlide,
    ProcessStep,
    TableSlide,
    TableSlideData,
    ThankYouSlide,
    TimelineSlide,
    TimelineStep,
    TitleSlide,
)
from app.schemas.template_blueprint import BlueprintCard, BlueprintSlide, PresentationBlueprint
from app.services.slide_text_limits import card_title_from_text

_MAX_CARDS = 6
_MAX_TIMELINE = 7
_MAX_PROCESS = 6
_MAX_COMPARISON_POINTS = 5
_MAX_TABLE_HEADERS = 6
_MAX_TABLE_ROWS = 8
_MAX_METRICS = 6
_MAX_KEY_POINTS = 4


def _card_items(cards, limit: int = _MAX_CARDS):
    return [CardItem(title=c.title, text=c.text) for c in cards[:limit]]


def _cards_from_blueprint(bp: BlueprintSlide) -> list[CardItem]:
    if bp.cards:
        items = _card_items(bp.cards)
    else:
        source_lines = [line for line in bp.bullets if line and line.strip()]
        if bp.subtitle and bp.subtitle.strip():
            source_lines.append(bp.subtitle.strip())
        if not source_lines:
            source_lines = [bp.title or "Содержание слайда"]
        items = [
            CardItem(
                title=card_title_from_text(text, index=index + 1),
                text=text,
            )
            for index, text in enumerate(source_lines[:_MAX_CARDS])
        ]
    while len(items) < 2:
        filler = bp.subtitle or bp.title or f"Пункт {len(items) + 1}"
        items.append(CardItem(title=f"Пункт {len(items) + 1}", text=filler))
    return items[:_MAX_CARDS]


def blueprint_to_presentation_slides(blueprint: PresentationBlueprint) -> PresentationSlides:
    slides = []
    for bp in blueprint.slides:
        slides.append(_convert_slide(bp))
    return PresentationSlides(slides=slides)


def _convert_slide(bp: BlueprintSlide):
    image = bp.image
    if bp.slide_type == "title":
        return TitleSlide(title=bp.title, subtitle=bp.subtitle, image=image, speaker_notes=bp.speaker_notes)
    if bp.slide_type == "conclusion":
        takeaways = [line for line in bp.bullets if line.strip()]
        if bp.subtitle and bp.subtitle.strip():
            takeaways.append(bp.subtitle.strip())
        if not takeaways:
            takeaways = [
                f"{card.title}: {card.text}" if card.text else card.title
                for card in _cards_from_blueprint(bp)
            ]
        while len(takeaways) < 2:
            takeaways.append(bp.title or "Итог презентации")
        return ConclusionSlide(
            title=bp.title,
            takeaways=takeaways[:5],
            image=image,
            speaker_notes=bp.speaker_notes,
        )
    if bp.slide_type == "thank_you":
        return ThankYouSlide(
            title=bp.title,
            subtitle=bp.subtitle,
            contact=None,
            image=image,
            speaker_notes=bp.speaker_notes,
        )
    if bp.slide_type == "cards" and bp.cards:
        return CardsSlide(
            title=bp.title,
            cards=_card_items(bp.cards),
            image=image,
            speaker_notes=bp.speaker_notes,
        )
    if bp.slide_type == "comparison" and bp.comparison:
        return ComparisonSlide(
            title=bp.title,
            left=ComparisonSide(
                heading=bp.comparison.left_heading,
                points=bp.comparison.left_points[:_MAX_COMPARISON_POINTS],
            ),
            right=ComparisonSide(
                heading=bp.comparison.right_heading,
                points=bp.comparison.right_points[:_MAX_COMPARISON_POINTS],
            ),
            image=image,
            speaker_notes=bp.speaker_notes,
        )
    if bp.slide_type == "timeline" and bp.timeline_steps:
        return TimelineSlide(
            title=bp.title,
            steps=[
                TimelineStep(label=s.label, description=s.description)
                for s in bp.timeline_steps[:_MAX_TIMELINE]
            ],
            image=image,
            speaker_notes=bp.speaker_notes,
        )
    if bp.slide_type == "process" and bp.process_steps:
        return ProcessSlide(
            title=bp.title,
            steps=[
                ProcessStep(title=s.label, description=s.description)
                for s in bp.process_steps[:_MAX_PROCESS]
            ],
            image=image,
            speaker_notes=bp.speaker_notes,
        )
    if bp.slide_type == "table" and bp.table:
        return TableSlide(
            title=bp.title,
            table=TableSlideData(
                headers=bp.table.headers[:_MAX_TABLE_HEADERS],
                rows=bp.table.rows[:_MAX_TABLE_ROWS],
            ),
            image=image,
            speaker_notes=bp.speaker_notes,
        )
    if bp.slide_type in ("kpi", "metrics") and bp.metrics:
        return KpiSlide(
            title=bp.title,
            metrics=[
                MetricItem(value=m.value, label=m.label, note=m.note) for m in bp.metrics[:_MAX_METRICS]
            ],
            image=image,
            speaker_notes=bp.speaker_notes,
        )
    if bp.slide_type == "diagram":
        points = bp.key_points or bp.bullets
        if not points and bp.cards:
            points = [f"{c.title}: {c.text}" for c in bp.cards[:4]]
        return DiagramSlide(
            title=bp.title,
            key_points=points[:_MAX_KEY_POINTS] or [bp.subtitle or bp.title],
            caption=bp.subtitle,
            image=image,
            speaker_notes=bp.speaker_notes,
        )
    return CardsSlide(
        title=bp.title,
        cards=_cards_from_blueprint(bp),
        image=image,
        speaker_notes=bp.speaker_notes,
    )
