from __future__ import annotations

from typing import List, Optional

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.ai.registry import chat_with_agent
from app.ai.types import ChatMessage
from app.config import get_settings
from app.models import User
from app.services import template_service
from app.services.source_file_parser import extract_source_text

settings = get_settings()

PRESENTATION_SYSTEM_PROMPT = (
    "Ты эксперт по созданию презентаций. На основе запроса пользователя и приложенных материалов "
    "составь структурированный план презентации на русском языке. "
    "Формат ответа: markdown, для каждого слайда заголовок (##) и 3–5 пунктов списка."
)


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

    template_block = ""
    template_name = None
    if template_id is not None:
        template = template_service.get_user_template(
            db,
            user_id=user.id,
            template_id=template_id,
        )
        template_name = template.name
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

    outline = await chat_with_agent(
        selected_agent,
        [
            ChatMessage(
                role="user",
                content=f"{PRESENTATION_SYSTEM_PROMPT}\n\n{user_message}",
            ),
        ],
    )

    return {
        "outline": outline,
        "agent_id": selected_agent,
        "template_id": template_id,
        "template_name": template_name,
        "source_files": source_names,
    }
