from __future__ import annotations

from dataclasses import dataclass
from typing import List

from app.schemas.semantic_slides import PresentationSlides, SemanticSlide, VISUAL_SLIDE_TYPES

QUALITY_THRESHOLD = 0.8
_MAX_BULLET_LIKE_ITEMS = 6


@dataclass
class SlideQualityReport:
    slide_index: int
    slide_type: str
    title: str
    score: float
    issues: List[str]


@dataclass
class PresentationQualityReport:
    average_score: float
    slide_reports: List[SlideQualityReport]
    type_diversity: float

    @property
    def passes(self) -> bool:
        return self.average_score >= QUALITY_THRESHOLD


def _visual_block_count(slide: SemanticSlide) -> int:
    slide_type = slide.type
    if slide_type == "kpi":
        return len(slide.metrics)
    if slide_type == "cards":
        return len(slide.cards)
    if slide_type == "comparison":
        return len(slide.left.points) + len(slide.right.points) + 2
    if slide_type in ("timeline", "process"):
        return len(slide.steps)
    if slide_type == "results":
        return len(slide.results) + (1 if slide.summary else 0)
    if slide_type == "table":
        return len(slide.table.headers) + len(slide.table.rows)
    if slide_type == "agenda":
        return len(slide.items)
    if slide_type == "problem":
        return len(slide.pain_points)
    if slide_type == "goals":
        return len(slide.goals)
    if slide_type == "conclusion":
        return len(slide.takeaways)
    if slide_type == "diagram":
        return len(slide.key_points) + (1 if slide.image.source != "none" else 0)
    if slide_type == "title":
        return 2 if slide.subtitle else 1
    if slide_type == "thank_you":
        return 2
    return 1


def _list_overload_penalty(slide: SemanticSlide) -> float:
    count = _visual_block_count(slide)
    if slide.type in VISUAL_SLIDE_TYPES and count > _MAX_BULLET_LIKE_ITEMS:
        return 0.2
    if slide.type in ("problem", "goals", "conclusion") and count > 5:
        return 0.15
    return 0.0


def score_slide(slide: SemanticSlide, index: int, total: int) -> SlideQualityReport:
    issues: List[str] = []
    score = 1.0

    blocks = _visual_block_count(slide)
    if slide.type in VISUAL_SLIDE_TYPES:
        if blocks < 2:
            score -= 0.35
            issues.append("мало визуальных блоков")
    elif slide.type in ("title", "thank_you"):
        if not slide.title.strip():
            score -= 0.4
            issues.append("пустой заголовок")
    else:
        if blocks < 2:
            score -= 0.25
            issues.append("слайд почти без структуры")

    if slide.type not in VISUAL_SLIDE_TYPES and slide.type not in ("title", "thank_you", "conclusion"):
        score -= 0.2
        issues.append("нет визуального шаблона")

    score -= _list_overload_penalty(slide)
    if blocks >= 3 and slide.type in VISUAL_SLIDE_TYPES:
        score = min(1.0, score + 0.1)

    if index == 0 and slide.type != "title":
        score -= 0.15
        issues.append("первый слайд должен быть title")
    if index == total - 1 and slide.type not in ("thank_you", "conclusion"):
        score -= 0.05

    score = max(0.0, min(1.0, score))
    return SlideQualityReport(
        slide_index=index,
        slide_type=slide.type,
        title=slide.title,
        score=round(score, 3),
        issues=issues,
    )


def score_presentation(presentation: PresentationSlides) -> PresentationQualityReport:
    total = len(presentation.slides)
    reports = [score_slide(slide, index, total) for index, slide in enumerate(presentation.slides)]
    if not reports:
        return PresentationQualityReport(average_score=0.0, slide_reports=[], type_diversity=0.0)

    types = {slide.type for slide in presentation.slides}
    visual_types = types & set(VISUAL_SLIDE_TYPES)
    type_diversity = len(visual_types) / max(1, len(VISUAL_SLIDE_TYPES))

    avg = sum(report.score for report in reports) / len(reports)
    diversity_bonus = min(0.12, type_diversity * 0.12)
    average_score = min(1.0, avg + diversity_bonus)

    return PresentationQualityReport(
        average_score=round(average_score, 3),
        slide_reports=reports,
        type_diversity=round(type_diversity, 3),
    )


def build_quality_feedback(report: PresentationQualityReport) -> str:
    weak = [r for r in report.slide_reports if r.score < QUALITY_THRESHOLD]
    if not weak:
        return ""
    lines = [
        "Улучши слайды с низким качеством. Запрещены слайды «заголовок + длинный список буллетов».",
        "Используй типы: kpi, cards, comparison, timeline, process, results, table, diagram, agenda.",
        f"Средний score: {report.average_score}, разнообразие типов: {report.type_diversity}.",
    ]
    for item in weak[:8]:
        lines.append(
            f"- Слайд {item.slide_index + 1} «{item.title}» ({item.slide_type}, score={item.score}): "
            + "; ".join(item.issues)
        )
    return "\n".join(lines)
