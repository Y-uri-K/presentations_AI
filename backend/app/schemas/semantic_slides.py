from __future__ import annotations

from typing import Annotated, List, Literal, Optional, Union

from pydantic import BaseModel, Field

from app.schemas.slides import SlideImageSpec

SlideType = Literal[
    "title",
    "agenda",
    "problem",
    "goals",
    "kpi",
    "cards",
    "comparison",
    "timeline",
    "process",
    "results",
    "table",
    "diagram",
    "conclusion",
    "thank_you",
]

VISUAL_SLIDE_TYPES = frozenset(
    {
        "kpi",
        "cards",
        "comparison",
        "timeline",
        "process",
        "results",
        "table",
        "diagram",
        "agenda",
    }
)


class SlideBase(BaseModel):
    title: str
    image: SlideImageSpec = Field(default_factory=SlideImageSpec)
    speaker_notes: Optional[str] = None


class MetricItem(BaseModel):
    value: str
    label: str
    note: Optional[str] = None


class CardItem(BaseModel):
    title: str
    text: str
    highlight: Optional[str] = None


class ComparisonSide(BaseModel):
    heading: str
    points: List[str] = Field(default_factory=list, max_length=5)


class TimelineStep(BaseModel):
    label: str
    description: Optional[str] = None


class ProcessStep(BaseModel):
    title: str
    description: Optional[str] = None


class ResultItem(BaseModel):
    label: str
    value: str
    trend: Optional[Literal["up", "down", "neutral"]] = None


class TableSlideData(BaseModel):
    headers: List[str] = Field(default_factory=list, max_length=6)
    rows: List[List[str]] = Field(default_factory=list, max_length=8)


class TitleSlide(SlideBase):
    type: Literal["title"] = "title"
    subtitle: Optional[str] = None


class AgendaSlide(SlideBase):
    type: Literal["agenda"] = "agenda"
    items: List[str] = Field(default_factory=list, min_length=2, max_length=8)


class ProblemSlide(SlideBase):
    type: Literal["problem"] = "problem"
    pain_points: List[str] = Field(default_factory=list, min_length=2, max_length=5)


class GoalsSlide(SlideBase):
    type: Literal["goals"] = "goals"
    goals: List[str] = Field(default_factory=list, min_length=2, max_length=5)


class KpiSlide(SlideBase):
    type: Literal["kpi"] = "kpi"
    metrics: List[MetricItem] = Field(default_factory=list, min_length=2, max_length=6)


class CardsSlide(SlideBase):
    type: Literal["cards"] = "cards"
    cards: List[CardItem] = Field(default_factory=list, min_length=2, max_length=6)


class ComparisonSlide(SlideBase):
    type: Literal["comparison"] = "comparison"
    left: ComparisonSide
    right: ComparisonSide


class TimelineSlide(SlideBase):
    type: Literal["timeline"] = "timeline"
    steps: List[TimelineStep] = Field(default_factory=list, min_length=3, max_length=7)


class ProcessSlide(SlideBase):
    type: Literal["process"] = "process"
    steps: List[ProcessStep] = Field(default_factory=list, min_length=3, max_length=6)


class ResultsSlide(SlideBase):
    type: Literal["results"] = "results"
    summary: Optional[str] = None
    results: List[ResultItem] = Field(default_factory=list, min_length=2, max_length=6)


class TableSlide(SlideBase):
    type: Literal["table"] = "table"
    table: TableSlideData


class DiagramSlide(SlideBase):
    type: Literal["diagram"] = "diagram"
    caption: Optional[str] = None
    key_points: List[str] = Field(default_factory=list, max_length=4)


class ConclusionSlide(SlideBase):
    type: Literal["conclusion"] = "conclusion"
    takeaways: List[str] = Field(default_factory=list, min_length=2, max_length=5)


class ThankYouSlide(SlideBase):
    type: Literal["thank_you"] = "thank_you"
    subtitle: Optional[str] = None
    contact: Optional[str] = None


SemanticSlide = Annotated[
    Union[
        TitleSlide,
        AgendaSlide,
        ProblemSlide,
        GoalsSlide,
        KpiSlide,
        CardsSlide,
        ComparisonSlide,
        TimelineSlide,
        ProcessSlide,
        ResultsSlide,
        TableSlide,
        DiagramSlide,
        ConclusionSlide,
        ThankYouSlide,
    ],
    Field(discriminator="type"),
]


class SemanticPlanItem(BaseModel):
    type: SlideType
    title: str
    intent: str = Field(description="Кратко: зачем этот слайд и какой визуальный формат")


class SemanticPlan(BaseModel):
    slides: List[SemanticPlanItem]


class PresentationSlides(BaseModel):
    slides: List[SemanticSlide]
