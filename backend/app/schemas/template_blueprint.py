from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

from app.schemas.slides import SlideImageSpec

SlideTypeName = Literal[
    "title",
    "section",
    "cards",
    "comparison",
    "timeline",
    "process",
    "table",
    "kpi",
    "diagram",
    "title_content",
    "agenda",
    "conclusion",
]


class ContentSlotSchema(BaseModel):
    slot_id: str
    role: str
    placeholder_idx: Optional[int] = None
    min_words: int = 5
    default_text: str = ""
    required: bool = True


class TemplateSlideSchema(BaseModel):
    """Структура одного слайда-образца из файла шаблона."""

    template_key: str
    slide_index: int
    layout_name: str
    slide_type: SlideTypeName
    title_slot: Optional[str] = None
    subtitle_slot: Optional[str] = None
    content_slots: List[ContentSlotSchema] = Field(default_factory=list)
    card_slots: List[str] = Field(default_factory=list)
    column_slots: List[str] = Field(default_factory=list)
    has_table: bool = False
    has_chart: bool = False
    has_picture: bool = False
    has_timeline: bool = False
    has_metrics: bool = False
    metric_slot_groups: List[List[str]] = Field(default_factory=list)
    required_fields: List[str] = Field(default_factory=list)


class TemplateCatalog(BaseModel):
  slides: List[TemplateSlideSchema] = Field(default_factory=list)

  def candidates(self, slide_type: str) -> List[TemplateSlideSchema]:
      return [s for s in self.slides if s.slide_type == slide_type] or self.slides

  def by_key(self, key: str) -> Optional[TemplateSlideSchema]:
      for slide in self.slides:
          if slide.template_key == key:
              return slide
      return None


class BlueprintCard(BaseModel):
    title: str
    text: str


class BlueprintColumn(BaseModel):
    heading: str
    points: List[str] = Field(default_factory=list)


class BlueprintMetric(BaseModel):
    value: str
    label: str
    note: Optional[str] = None


class BlueprintTimelineStep(BaseModel):
    label: str
    description: Optional[str] = None


class BlueprintTable(BaseModel):
    headers: List[str] = Field(default_factory=list)
    rows: List[List[str]] = Field(default_factory=list)


class BlueprintComparison(BaseModel):
    left_heading: str
    left_points: List[str] = Field(default_factory=list)
    right_heading: str
    right_points: List[str] = Field(default_factory=list)


class BlueprintSlide(BaseModel):
    slide_type: SlideTypeName
    template_key: str
    topic: str = ""
    title: str
    subtitle: Optional[str] = None
    bullets: List[str] = Field(default_factory=list)
    cards: List[BlueprintCard] = Field(default_factory=list)
    columns: List[BlueprintColumn] = Field(default_factory=list)
    metrics: List[BlueprintMetric] = Field(default_factory=list)
    timeline_steps: List[BlueprintTimelineStep] = Field(default_factory=list)
    process_steps: List[BlueprintTimelineStep] = Field(default_factory=list)
    table: Optional[BlueprintTable] = None
    comparison: Optional[BlueprintComparison] = None
    key_points: List[str] = Field(default_factory=list)
    entities: Dict[str, Any] = Field(default_factory=dict)
    slot_texts: Dict[str, str] = Field(default_factory=dict)
    image: SlideImageSpec = Field(default_factory=SlideImageSpec)
    speaker_notes: Optional[str] = None


class PresentationBlueprint(BaseModel):
    title: str
    slides: List[BlueprintSlide] = Field(default_factory=list)


class SlideQualityScores(BaseModel):
    content_completeness: float = 0.0
    visual_completeness: float = 0.0
    template_coverage: float = 0.0
    information_density: float = 0.0

    @property
    def average(self) -> float:
        return (
            self.content_completeness
            + self.visual_completeness
            + self.template_coverage
            + self.information_density
        ) / 4.0
