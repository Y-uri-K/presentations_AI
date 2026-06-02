from __future__ import annotations

import logging
from typing import Optional

from app.schemas.semantic_slides import SemanticSlide
from app.services.image_normalizer import normalize_image_for_pptx
from app.services.slide_renderers import render_semantic_slide, render_semantic_slide_notes
from app.services.slide_renderers.context import RenderContext
from app.services.slide_renderers.drawing import count_pictures_on_slide
from app.services.slide_renderers.image_insert import insert_slide_image_early, insert_slide_image_verified
from app.services.slide_text_controller import enforce_slide_text_control
from app.services.pptx_fonts import DEFAULT_PRESENTATION_FONT, apply_font_family_preserve_to_slide
from app.services.template_style_applier import apply_slide_background
from app.services.template_style_extractor import UserTemplateStyle

logger = logging.getLogger(__name__)


def _text_preview(spec: SemanticSlide, limit: int = 60) -> str:
    title = (spec.title or "").strip()
    return title[:limit] if title else spec.type


def build_slide_controlled(
    *,
    slide,
    spec: SemanticSlide,
    slide_index: int,
    slide_width: int,
    slide_height: int,
    user_style: UserTemplateStyle,
    image_bytes: Optional[bytes],
    layout_variant: str,
) -> bool:
    """
    Поэтапная сборка одного слайда с логированием.
    Возвращает True, если сгенерированное изображение вставлено (или не требовалось).
    """
    text_report = enforce_slide_text_control(spec, slide_index=slide_index)
    if text_report.has_warnings:
        logger.warning(
            "Слайд %s: текстовый контроль обнаружил замечания (%s)",
            slide_index + 1,
            "; ".join(issue.message for issue in text_report.issues),
        )

    has_image_request = spec.image.source == "generate" or spec.image.source == "materials"
    logger.info(
        "Слайд %s «%s»: type=%s, variant=%s, image_spec=%s, bytes=%s",
        slide_index + 1,
        _text_preview(spec),
        spec.type,
        layout_variant,
        spec.image.source,
        len(image_bytes) if image_bytes else 0,
    )

    apply_slide_background(
        slide,
        user_style=user_style,
        slide_width=slide_width,
        slide_height=slide_height,
    )

    normalized_image: Optional[bytes] = None
    if image_bytes:
        normalized_image = normalize_image_for_pptx(image_bytes)
        if normalized_image is None:
            logger.warning(
                "Слайд %s: изображение не нормализовано (%s байт), пропуск вставки",
                slide_index + 1,
                len(image_bytes),
            )
        else:
            logger.info(
                "Слайд %s: JPEG для PPTX %s байт",
                slide_index + 1,
                len(normalized_image),
            )

    image_ok = True
    if has_image_request and normalized_image:
        early_ctx = RenderContext(
            slide=slide,
            spec=spec,
            slide_width=slide_width,
            slide_height=slide_height,
            user_style=user_style,
            image_bytes=normalized_image,
            slide_index=slide_index,
            layout_variant=layout_variant,
        )
        image_ok = insert_slide_image_early(early_ctx)
        if image_ok:
            logger.info(
                "Слайд %s: иллюстрация под контентом (placement=%s)",
                slide_index + 1,
                spec.image.placement or user_style.content_image_side,
            )
        else:
            logger.error("Слайд %s: вставка иллюстрации не удалась", slide_index + 1)
    elif has_image_request and not normalized_image:
        image_ok = False
        logger.warning("Слайд %s: ожидалось изображение, но данных нет", slide_index + 1)

    ctx = RenderContext(
        slide=slide,
        spec=spec,
        slide_width=slide_width,
        slide_height=slide_height,
        user_style=user_style,
        image_bytes=normalized_image if has_image_request else None,
        slide_index=slide_index,
        layout_variant=layout_variant,
    )

    render_semantic_slide(ctx, insert_image=False)
    render_semantic_slide_notes(ctx)
    font_name = ctx.user_style.font_family or DEFAULT_PRESENTATION_FONT
    apply_font_family_preserve_to_slide(slide, font_name)

    shape_count = len(slide.shapes)
    logger.info(
        "Слайд %s: готово — фигур=%s, image_ok=%s",
        slide_index + 1,
        shape_count,
        image_ok,
    )
    return image_ok
