from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from pptx.dml.color import RGBColor

from app.schemas.semantic_slides import SemanticSlide
from app.services.slide_palette_colors import palette_rgb
from app.services.template_style_extractor import UserTemplateStyle


@dataclass
class RenderContext:
    slide: object
    spec: SemanticSlide
    slide_width: int
    slide_height: int
    user_style: UserTemplateStyle
    image_bytes: Optional[bytes] = None
    slide_index: int = 0
    layout_variant: str = "default"

    @property
    def has_image_zone(self) -> bool:
        """Зона иллюстрации зарезервирована (даже до вставки байтов)."""
        if self.image_bytes:
            return True
        return self.spec.image.source in ("generate", "materials")

    @property
    def accent(self) -> RGBColor:
        return palette_rgb(self.user_style, "accent")

    @property
    def text_color(self) -> RGBColor:
        if self.user_style.body_text_style.rgb is not None:
            return self.user_style.body_text_style.rgb
        return palette_rgb(self.user_style, "dark")

    @property
    def title_color(self) -> RGBColor:
        if self.user_style.title_text_style.rgb is not None:
            return self.user_style.title_text_style.rgb
        return palette_rgb(self.user_style, "accent")
