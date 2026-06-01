from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Optional

from app.config import get_settings

if TYPE_CHECKING:
    from app.schemas.template_blueprint import TemplateCatalog
from app.services.pdf_template_style_extractor import extract_user_template_style_from_pdf
from app.services.template_ai_style_analyzer import analyze_template_style_with_polza
from app.services.template_slide_inspector import (
    extract_largest_background_image_pptx,
    inspect_template_slides,
)
from app.services.template_geometry_analyzer import TemplateGeometryReport, analyze_template_geometry
from app.services.template_palette import apply_palette_to_style, extract_template_palette
from app.services.template_style_extractor import UserTemplateStyle, extract_user_template_style

logger = logging.getLogger(__name__)
settings = get_settings()


def _apply_geometry_to_style(base: UserTemplateStyle, geometry: TemplateGeometryReport) -> UserTemplateStyle:
    schemes: list[str] = []
    for name, count in geometry.scheme_counts.items():
        schemes.extend([name] * min(count, 2))
    schemes = sorted(set(schemes + geometry.title_slide.diagram_schemes))[:12]

    base.title_layout_pattern = geometry.title_slide.layout_pattern
    base.title_logo_zone = geometry.title_logo_zone
    base.title_hero_mode = geometry.title_hero_mode
    base.content_image_side = geometry.recommended_content_image_side
    base.diagram_schemes = schemes
    base.shape_type_counts = dict(geometry.shape_type_counts)
    return base


async def resolve_user_template_style(
    template_bytes: bytes,
    template_file_type: str,
    *,
    catalog: Optional["TemplateCatalog"] = None,
) -> UserTemplateStyle:
    if template_file_type == "pdf":
        base = extract_user_template_style_from_pdf(template_bytes)
    else:
        base = extract_user_template_style(template_bytes)

    samples = inspect_template_slides(
        template_bytes,
        template_file_type,
        max_slides=settings.presentation_max_slides,
    )
    logger.info("Инспекция шаблона: %s слайдов проанализировано", len(samples))

    geometry: TemplateGeometryReport | None = None
    palette_hex = extract_template_palette(
        template_bytes,
        template_file_type,
        max_colors=6,
    )
    base.palette_hex = palette_hex
    base = apply_palette_to_style(base, palette_hex)

    if template_file_type == "pptx":
        geometry = analyze_template_geometry(
            template_bytes,
            max_slides=settings.presentation_max_slides,
        )
        base = _apply_geometry_to_style(base, geometry)

    if template_file_type == "pptx" and any(sample.has_background_image for sample in samples):
        bg_image = extract_largest_background_image_pptx(
            template_bytes,
            max_slides=settings.presentation_max_slides,
        )
        if bg_image:
            base.background_image = bg_image
            logger.info("Фоновое изображение из шаблона: %s байт", len(bg_image))

    if settings.presentation_template_ai_analysis:
        base = await analyze_template_style_with_polza(
            samples, base, catalog=catalog, geometry=geometry
        )
        base = apply_palette_to_style(base, palette_hex)

    return base
