from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

ImageSource = Literal["none", "materials", "generate"]


class SlideImageSpec(BaseModel):
    source: ImageSource = "none"
    material_ref: Optional[str] = Field(
        default=None,
        description='Ссылка на картинку из материалов, например "report.pdf:0"',
    )
    prompt: Optional[str] = Field(default=None, description="Промпт для генерации изображения")
    placement: Optional[Literal["left", "right", "vertical"]] = Field(
        default="right",
        description="Расположение картинки на слайде (из layout SECTION в XML)",
    )


from app.schemas.semantic_slides import (  # noqa: E402,F401
    CardItem,
    ComparisonSide,
    MetricItem,
    PresentationSlides,
    ProcessStep,
    ResultItem,
    SemanticPlan,
    SemanticPlanItem,
    SemanticSlide,
    SlideType,
    TableSlideData,
    AgendaSlide,
    CardsSlide,
    ComparisonSlide,
    ConclusionSlide,
    DiagramSlide,
    GoalsSlide,
    KpiSlide,
    ProblemSlide,
    ProcessSlide,
    ResultsSlide,
    TableSlide,
    ThankYouSlide,
    TimelineSlide,
    TitleSlide,
    TimelineStep,
    ProcessStep,
    VISUAL_SLIDE_TYPES,
)

SlideLayout = SlideType  # legacy alias
