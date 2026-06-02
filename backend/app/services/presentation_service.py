from __future__ import annotations

import logging
import re
import time
from typing import List, Optional

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.registry import chat_with_agent_resilient
from app.ai.types import ChatMessage
from app.config import get_settings
from app.models import Presentation, PresentationSourceFile, User
from app.services import template_service
from app.services.outline_limits import count_outline_slides, ensure_outline_within_limit
from app.services.presentation_gamma.outline import (
    extract_presentation_title,
    format_outline_prompt,
    normalize_stored_outline,
)
from app.services.source_file_parser import extract_source_text

settings = get_settings()
logger = logging.getLogger(__name__)


def _sanitize_title(title: str, fallback: str = "Презентация") -> str:
    cleaned = re.sub(r"\s+", " ", title.strip())
    return cleaned[:255] if cleaned else fallback


def _derive_title(outline: str, prompt: str) -> str:
    return extract_presentation_title(outline, fallback=prompt.strip() or "Презентация")


def list_user_presentations(db: Session, user_id: int) -> list[Presentation]:
    return list(
        db.scalars(
            select(Presentation)
            .where(Presentation.user_id == user_id)
            .order_by(Presentation.updated_at.desc(), Presentation.created_at.desc())
        )
    )


def rename_presentation(
    db: Session,
    *,
    user: User,
    presentation_id: int,
    title: str,
) -> Presentation:
    from app.services.presentation_build_service import get_user_presentation

    presentation = get_user_presentation(db, user_id=user.id, presentation_id=presentation_id)
    presentation.title = _sanitize_title(title, presentation.title)
    db.commit()
    db.refresh(presentation)
    return presentation


def delete_presentation(db: Session, *, user: User, presentation_id: int) -> None:
    from app.services.presentation_build_service import get_user_presentation

    presentation = get_user_presentation(db, user_id=user.id, presentation_id=presentation_id)
    db.delete(presentation)
    db.commit()


async def create_presentation_outline(
    db: Session,
    *,
    user: User,
    prompt: str,
    agent_id: Optional[str],
    template_id: Optional[int],
    source_files: List[UploadFile],
) -> dict:
    cleaned_prompt = prompt.strip()
    if not cleaned_prompt and not source_files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Введите описание презентации или приложите файл",
        )

    if len(source_files) > settings.presentation_source_max_files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Не более {settings.presentation_source_max_files} файлов за раз",
        )

    max_bytes = settings.presentation_source_max_size_mb * 1024 * 1024
    source_names: List[str] = []
    source_blocks: List[str] = []
    stored_sources: List[tuple[str, bytes]] = []

    for upload in source_files:
        filename = upload.filename or "source.txt"
        content = await upload.read()
        if len(content) > max_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Максимальный размер файла — {settings.presentation_source_max_size_mb} МБ",
            )
        text = extract_source_text(filename=filename, content=content)
        source_names.append(filename)
        source_blocks.append(f"### {filename}\n{text}")
        stored_sources.append((filename, content))

    template_block = ""
    template_name = None
    template_file_type = None
    if template_id is not None:
        template = template_service.get_user_template(
            db,
            user_id=user.id,
            template_id=template_id,
        )
        template_name = template.name
        template_file_type = template.file_type
        template_block = (
            f"\n\nВыбранный шаблон оформления: «{template.name}» ({template.file_type.upper()}). "
            "Учитывай его стиль при структуре и тоне презентации."
        )

    user_message_parts = []
    if cleaned_prompt:
        user_message_parts.append(f"Запрос пользователя:\n{cleaned_prompt}")
    if source_blocks:
        user_message_parts.append("Исходные материалы:\n" + "\n\n".join(source_blocks))
    if template_block:
        user_message_parts.append(template_block.strip())

    user_message = "\n\n".join(user_message_parts)
    selected_agent = agent_id or settings.presentation_default_agent

    outline_prompt = format_outline_prompt(
        text_content=settings.presentation_text_content,
        tone=settings.presentation_tone,
        audience=settings.presentation_audience,
        scenario=settings.presentation_scenario,
    )
    logger.info(
        "Создание плана (gamma-style): агент=%s, макс. %s слайдов...",
        selected_agent,
        settings.presentation_max_slides,
    )
    started = time.perf_counter()
    raw_outline = await chat_with_agent_resilient(
        selected_agent,
        [
            ChatMessage(
                role="user",
                content=f"{outline_prompt}\n\n{user_message}",
            ),
        ],
    )
    title, outline = normalize_stored_outline(
        raw_outline,
        fallback_title=cleaned_prompt or "Презентация",
    )
    logger.info(
        "План создан за %.1f с: «%s», тем=%s",
        time.perf_counter() - started,
        title,
        count_outline_slides(outline),
    )

    presentation = Presentation(
        user_id=user.id,
        template_id=template_id,
        agent_id=selected_agent,
        title=title,
        prompt=cleaned_prompt or None,
        outline=outline,
        status="draft",
        source_filenames=source_names or None,
    )
    db.add(presentation)
    db.flush()

    for filename, content in stored_sources:
        db.add(
            PresentationSourceFile(
                presentation_id=presentation.id,
                filename=filename,
                content=content,
            )
        )

    db.commit()
    db.refresh(presentation)

    return {
        "id": presentation.id,
        "outline": outline,
        "agent_id": selected_agent,
        "template_id": template_id,
        "template_name": template_name,
        "template_file_type": template_file_type,
        "source_files": source_names,
        "status": presentation.status,
    }


def update_presentation_outline(
    db: Session,
    *,
    user: User,
    presentation_id: int,
    outline: str,
) -> Presentation:
    from app.services.presentation_build_service import get_user_presentation

    presentation = get_user_presentation(db, user_id=user.id, presentation_id=presentation_id)
    cleaned = ensure_outline_within_limit(outline)

    presentation.outline = cleaned
    presentation.title = _derive_title(cleaned, presentation.prompt or "")

    if presentation.status in ("ready", "failed"):
        presentation.status = "draft"
        presentation.pptx_data = None
        presentation.slides_json = None
        presentation.error_message = None

    db.commit()
    db.refresh(presentation)
    return presentation
