from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from app.schemas.template_blueprint import PresentationBlueprint, TemplateCatalog
from app.services.template_driven.constants import MAX_SAME_LAYOUT_IN_ROW, SLIDE_SCORE_THRESHOLD
from app.services.template_driven.quality import score_blueprint_slide
from app.services.template_driven.text_utils import is_placeholder_text, word_count


@dataclass
class ValidationIssue:
    slide_index: int
    field: str
    message: str


@dataclass
class ValidationReport:
    ok: bool
    issues: List[ValidationIssue] = field(default_factory=list)
    scores: List[float] = field(default_factory=list)


def validate_blueprint(
    blueprint: PresentationBlueprint,
    catalog: TemplateCatalog,
) -> ValidationReport:
    issues: List[ValidationIssue] = []
    scores: List[float] = []
    prev_types: List[str] = []

    for index, slide in enumerate(blueprint.slides):
        tpl = catalog.by_key(slide.template_key)
        if tpl is None:
            issues.append(
                ValidationIssue(
                    slide_index=index,
                    field="template_key",
                    message=f"Неизвестный макет: {slide.template_key}",
                )
            )

        if not slide.title or is_placeholder_text(slide.title):
            issues.append(
                ValidationIssue(slide_index=index, field="title", message="Пустой или placeholder заголовок")
            )
        elif word_count(slide.title) < 3:
            issues.append(
                ValidationIssue(slide_index=index, field="title", message="Заголовок слишком короткий")
            )

        if slide.subtitle and is_placeholder_text(slide.subtitle):
            issues.append(
                ValidationIssue(slide_index=index, field="subtitle", message="Placeholder в подзаголовке")
            )

        for slot_id, text in slide.slot_texts.items():
            if is_placeholder_text(text):
                issues.append(
                    ValidationIssue(
                        slide_index=index,
                        field=slot_id,
                        message=f"Placeholder в слоте {slot_id}",
                    )
                )

        if slide.slide_type == "cards":
            min_cards = 2
            if tpl and tpl.card_slots:
                min_cards = min(2, max(1, len(tpl.card_slots)))
            if len(slide.cards) < min_cards:
                issues.append(
                    ValidationIssue(slide_index=index, field="cards", message="Недостаточно карточек")
                )
            for card_index, card in enumerate(slide.cards):
                if is_placeholder_text(card.text):
                    issues.append(
                        ValidationIssue(
                            slide_index=index,
                            field=f"cards[{card_index}]",
                            message="Пустая карточка",
                        )
                    )
                elif word_count(card.text) < 15:
                    issues.append(
                        ValidationIssue(
                            slide_index=index,
                            field=f"cards[{card_index}]",
                            message="Карточка слишком короткая",
                        )
                    )

        if slide.slide_type == "comparison" and slide.comparison:
            if len(slide.comparison.left_points) < 3 or len(slide.comparison.right_points) < 3:
                issues.append(
                    ValidationIssue(
                        slide_index=index, field="comparison", message="Мало пунктов в колонках сравнения"
                    )
                )

        if slide.slide_type == "table" and slide.table:
            if not slide.table.headers or not slide.table.rows:
                issues.append(
                    ValidationIssue(slide_index=index, field="table", message="Пустая таблица")
                )

        if slide.slide_type in ("timeline", "process") and len(slide.timeline_steps) + len(slide.process_steps) < 3:
            issues.append(
                ValidationIssue(slide_index=index, field="steps", message="Мало шагов timeline/process")
            )

        if len(prev_types) >= MAX_SAME_LAYOUT_IN_ROW and all(
            t == slide.slide_type for t in prev_types[-MAX_SAME_LAYOUT_IN_ROW:]
        ):
            issues.append(
                ValidationIssue(
                    slide_index=index,
                    field="slide_type",
                    message=f"Тип «{slide.slide_type}» повторяется более {MAX_SAME_LAYOUT_IN_ROW} раз подряд",
                )
            )
        prev_types.append(slide.slide_type)

        slide_score = score_blueprint_slide(slide, tpl).average
        scores.append(slide_score)
        if slide_score < SLIDE_SCORE_THRESHOLD:
            issues.append(
                ValidationIssue(
                    slide_index=index,
                    field="score",
                    message=f"Низкий score слайда: {slide_score:.2f}",
                )
            )

    return ValidationReport(ok=len(issues) == 0, issues=issues, scores=scores)
