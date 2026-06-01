from __future__ import annotations

import asyncio
import logging
import time
from typing import Dict, List, Tuple

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.ai.providers.polza_image import generate_slide_image_bytes
from app.config import get_settings
from app.database import SessionLocal
from app.models import Presentation, User
from app.schemas.slides import PresentationSlides, SlideImageSpec
from app.services import template_service
from app.services.image_normalizer import normalize_image_for_pptx
from app.services.pptx_builder import build_pptx_from_template
from app.services.slide_image_plan import apply_slide_image_plan, clear_generated_image_requests
from app.services.slide_content_density import enrich_presentation_from_outline
from app.services.slide_text_controller import enforce_presentation_text_control
from app.services.template_driven.pipeline import (
    analyze_template_for_build,
    generate_presentation_blueprint,
)
from app.services.template_style_service import resolve_user_template_style
from app.services.presentation_gamma.outline import extract_presentation_title
from app.services.slide_planner import available_refs_from_sources, plan_slides_from_outline
from app.services.source_image_extractor import (
    extract_images_from_sources,
    resolve_material_image,
)

settings = get_settings()
logger = logging.getLogger(__name__)


def _set_build_stage(db: Session, presentation_id: int, stage: str) -> None:
    presentation = db.get(Presentation, presentation_id)
    if presentation is not None:
        presentation.build_stage = stage
        db.commit()


def run_build_in_background(
    presentation_id: int,
    user_id: int,
    *,
    generate_images: bool = True,
) -> None:
    """Фоновая сборка (FastAPI BackgroundTasks)."""
    try:
        asyncio.run(_run_build_async(presentation_id, user_id, generate_images=generate_images))
    except Exception:
        logger.exception("Фоновая сборка id=%s: необработанная ошибка", presentation_id)
        db = SessionLocal()
        try:
            presentation = db.get(Presentation, presentation_id)
            if presentation is not None and presentation.status == "building":
                presentation.status = "failed"
                presentation.error_message = "Внутренняя ошибка сборки. См. логи backend."
                presentation.build_stage = "failed"
                db.commit()
        finally:
            db.close()


async def _run_build_async(
    presentation_id: int,
    user_id: int,
    *,
    generate_images: bool = True,
) -> None:
    db = SessionLocal()
    try:
        user = db.get(User, user_id)
        if user is None:
            logger.error("Фоновая сборка: пользователь %s не найден", user_id)
            return
        _set_build_stage(db, presentation_id, "started")
        await build_presentation_file(
            db,
            user=user,
            presentation_id=presentation_id,
            generate_images=generate_images,
        )
        _set_build_stage(db, presentation_id, "done")
    except HTTPException as exc:
        logger.error("Фоновая сборка id=%s: %s", presentation_id, exc.detail)
    except Exception as exc:
        logger.exception("Фоновая сборка id=%s: %s", presentation_id, exc)
    finally:
        db.close()


def get_user_presentation(db: Session, *, user_id: int, presentation_id: int) -> Presentation:
    presentation = db.scalar(
        select(Presentation)
        .where(
            Presentation.id == presentation_id,
            Presentation.user_id == user_id,
        )
        .options(selectinload(Presentation.source_files))
    )
    if presentation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Презентация не найдена")
    return presentation


def _cap_generated_image_requests(slides: PresentationSlides) -> List[int]:
    """Оставляет generate только для первых N слайдов — остальное ускоряет сборку."""
    indices: List[int] = []
    for index, slide in enumerate(slides.slides):
        if slide.image.source == "generate":
            indices.append(index)

    limit = settings.presentation_max_generated_images
    allowed = indices[:limit]
    skipped = indices[limit:]
    for index in skipped:
        slides.slides[index].image = SlideImageSpec(source="none")
    if skipped:
        logger.info(
            "Генерация картинок: лимит %s, пропущены слайды %s",
            limit,
            [i + 1 for i in skipped],
        )
    return allowed


async def _generate_slide_image(index: int, slide) -> Tuple[int, bytes | None]:
    hint = slide.image.prompt
    if slide.type == "diagram" and not hint:
        hint = f"Диаграмма: {slide.title}"
    started = time.perf_counter()
    logger.info("Картинка слайд %s «%s»: старт", index + 1, slide.title)
    try:
        image_bytes, mime = await generate_slide_image_bytes(
            slide_title=slide.title,
            image_hint=hint,
        )
        logger.info(
            "Картинка слайд %s «%s»: готово (%s, %s байт, %.1f с)",
            index + 1,
            slide.title,
            mime,
            len(image_bytes),
            time.perf_counter() - started,
        )
        normalized = normalize_image_for_pptx(image_bytes, mime_type=mime)
        if normalized is None:
            logger.error(
                "Картинка слайд %s «%s»: не удалось нормализовать (%s байт), пропуск",
                index + 1,
                slide.title,
                len(image_bytes),
            )
            return index, None
        return index, normalized
    except HTTPException as exc:
        logger.warning(
            "Картинка слайд %s «%s»: пропуск за %.1f с — %s",
            index + 1,
            slide.title,
            time.perf_counter() - started,
            exc.detail,
        )
        return index, None


async def _resolve_slide_images(
    slides: PresentationSlides,
    sources: List[tuple[str, bytes]],
) -> Dict[int, bytes]:
    by_ref = extract_images_from_sources(sources)
    slide_images: Dict[int, bytes] = {}

    for index, slide in enumerate(slides.slides):
        image_spec: SlideImageSpec = slide.image
        if image_spec.source == "materials":
            if not image_spec.material_ref:
                continue
            try:
                extracted = resolve_material_image(image_spec.material_ref, by_ref)
                normalized = normalize_image_for_pptx(
                    extracted.content,
                    mime_type=getattr(extracted, "mime_type", None),
                )
                if normalized:
                    slide_images[index] = normalized
            except HTTPException:
                continue

    for index, slide in enumerate(slides.slides):
        if slide.image.source == "generate":
            logger.info(
                "Запрос изображения: слайд %s «%s», prompt=%s, placement=%s",
                index + 1,
                slide.title,
                slide.image.prompt,
                slide.image.placement,
            )

    generate_indices = _cap_generated_image_requests(slides)
    if generate_indices:
        logger.info("Параллельная генерация %s изображений (лимит %s)...", len(generate_indices), settings.presentation_max_generated_images)
        started = time.perf_counter()
        results = await asyncio.gather(
            *[_generate_slide_image(index, slides.slides[index]) for index in generate_indices]
        )
        for index, image_bytes in results:
            if image_bytes is not None:
                slide_images[index] = image_bytes
        logger.info("Генерация изображений завершена за %.1f с", time.perf_counter() - started)

    generate_requested = sum(1 for s in slides.slides if s.image.source == "generate")
    logger.info(
        "Изображения в PPTX: всего %s (AI запрошено после лимита=%s, из материалов=%s)",
        len(slide_images),
        generate_requested,
        sum(1 for s in slides.slides if s.image.source == "materials"),
    )
    return slide_images


async def build_presentation_file(
    db: Session,
    *,
    user: User,
    presentation_id: int,
    generate_images: bool = True,
) -> Presentation:
    build_started = time.perf_counter()
    logger.info(
        "=== Сборка презентации id=%s: старт (generate_images=%s) ===",
        presentation_id,
        generate_images,
    )

    presentation = get_user_presentation(db, user_id=user.id, presentation_id=presentation_id)

    if presentation.template_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Выберите шаблон перед сборкой презентации",
        )

    template = template_service.get_user_template(
        db,
        user_id=user.id,
        template_id=presentation.template_id,
    )
    template_bytes = bytes(template.file_data)
    template_name = template.name
    sources = [(item.filename, bytes(item.content)) for item in presentation.source_files]
    outline = presentation.outline
    agent_id = presentation.agent_id
    presentation_prompt = presentation.prompt

    presentation.status = "building"
    presentation.error_message = None
    presentation.build_stage = "started"
    db.commit()

    try:
        available_refs = available_refs_from_sources(sources)

        deck_title = extract_presentation_title(
            outline,
            fallback=presentation.title or presentation_prompt or "Презентация",
        )

        if settings.presentation_use_template_driven and template.file_type == "pptx":
            _set_build_stage(db, presentation_id, "template_analysis")
            stage = time.perf_counter()
            analyzed = await analyze_template_for_build(template_bytes)
            logger.info("Этап «анализ шаблона»: %.1f с", time.perf_counter() - stage)

            _set_build_stage(db, presentation_id, "blueprint")
            stage = time.perf_counter()
            blueprint, slides = await generate_presentation_blueprint(
                analyzed,
                agent_id=agent_id,
                outline=outline,
                title=deck_title,
                presentation_prompt=presentation_prompt,
            )
            logger.info(
                "Этап «макеты слайдов»: %s слайдов за %.1f с",
                len(slides.slides),
                time.perf_counter() - stage,
            )
            enrich_presentation_from_outline(slides, outline, max_items_per_slide=3)
            enforce_presentation_text_control(slides)

            user_style = analyzed.user_style
            if user_style is None:
                user_style = await resolve_user_template_style(
                    template_bytes,
                    template.file_type,
                    catalog=analyzed.catalog,
                )

            apply_slide_image_plan(
                slides,
                presentation_prompt=presentation_prompt,
                content_image_side=user_style.content_image_side,
                enabled=generate_images,
            )
            _set_build_stage(db, presentation_id, "images")
            stage = time.perf_counter()
            slide_images = await _resolve_slide_images(slides, sources)
            logger.info("Этап «изображения»: %.1f с", time.perf_counter() - stage)

            _set_build_stage(db, presentation_id, "pptx_fill")
            stage = time.perf_counter()
            pptx_bytes = build_pptx_from_template(
                template_bytes=template_bytes,
                template_file_type=template.file_type,
                slides=slides,
                slide_images=slide_images,
                user_style=user_style,
            )
            logger.info(
                "Этап «PPTX (стиль шаблона)»: %.1f с, %s КБ, элементы=%s",
                time.perf_counter() - stage,
                len(pptx_bytes) // 1024,
                user_style.key_elements,
            )
        else:
            _set_build_stage(db, presentation_id, "content_plan")
            stage = time.perf_counter()
            slides = await plan_slides_from_outline(
                agent_id=agent_id,
                outline=outline,
                available_image_refs=available_refs,
                template_name=template_name,
                presentation_prompt=presentation_prompt,
                presentation_title=deck_title,
            )
            logger.info(
                "Этап «структура слайдов»: %s слайдов за %.1f с",
                len(slides.slides),
                time.perf_counter() - stage,
            )
            enrich_presentation_from_outline(slides, outline, max_items_per_slide=3)
            enforce_presentation_text_control(slides)
            if not generate_images:
                clear_generated_image_requests(slides)

            stage = time.perf_counter()
            slide_images = await _resolve_slide_images(slides, sources)
            logger.info("Этап «изображения»: %.1f с", time.perf_counter() - stage)

            stage = time.perf_counter()
            user_style = await resolve_user_template_style(
                template_bytes,
                template.file_type,
            )
            logger.info("Этап «стиль шаблона»: %.1f с", time.perf_counter() - stage)

            stage = time.perf_counter()
            pptx_bytes = build_pptx_from_template(
                template_bytes=template_bytes,
                template_file_type=template.file_type,
                slides=slides,
                slide_images=slide_images,
                user_style=user_style,
            )
            logger.info(
                "Этап «PPTX»: %.1f с, размер %s КБ",
                time.perf_counter() - stage,
                len(pptx_bytes) // 1024,
            )

        max_pptx = settings.presentation_pptx_max_size_mb * 1024 * 1024
        if len(pptx_bytes) > max_pptx:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Файл презентации превышает {settings.presentation_pptx_max_size_mb} МБ",
            )

        presentation.slides_json = slides.model_dump(mode="json")
        presentation.pptx_data = pptx_bytes
        presentation.status = "ready"
        if slides.slides and slides.slides[0].title:
            presentation.title = slides.slides[0].title[:255]
    except HTTPException as exc:
        logger.error(
            "Сборка презентации id=%s: HTTP %s — %s (%.1f с)",
            presentation_id,
            exc.status_code,
            exc.detail,
            time.perf_counter() - build_started,
        )
        presentation.status = "failed"
        presentation.error_message = str(exc.detail)
        db.commit()
        raise
    except Exception as exc:
        logger.exception(
            "Ошибка сборки презентации id=%s за %.1f с",
            presentation_id,
            time.perf_counter() - build_started,
        )
        presentation.status = "failed"
        presentation.error_message = str(exc)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Не удалось собрать презентацию: {exc}",
        ) from exc

    db.commit()
    db.refresh(presentation)
    logger.info(
        "=== Сборка презентации id=%s: готово за %.1f с ===",
        presentation_id,
        time.perf_counter() - build_started,
    )
    return presentation
