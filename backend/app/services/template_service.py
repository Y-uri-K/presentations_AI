from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import User, UserTemplate

settings = get_settings()

ALLOWED_EXTENSIONS = {".pptx", ".pdf"}
MIME_BY_TYPE = {
    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "pdf": "application/pdf",
}
MAGIC_CHECKS = {
    "pptx": (b"PK\x03\x04", b"PK\x05\x06"),
    "pdf": (b"%PDF",),
}


def _max_bytes() -> int:
    return settings.template_max_size_mb * 1024 * 1024


def _detect_file_type(filename: str, content: bytes) -> str:
    extension = Path(filename).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Допустимы только файлы .pptx и .pdf",
        )

    file_type = extension.lstrip(".")
    valid_magic = any(content.startswith(magic) for magic in MAGIC_CHECKS[file_type])
    if not valid_magic:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Файл не похож на корректный {extension.upper()}",
        )
    return file_type


def _sanitize_display_name(name: str, fallback: str) -> str:
    cleaned = re.sub(r"\s+", " ", name.strip())
    return cleaned[:255] if cleaned else fallback


def list_user_templates(db: Session, user_id: int) -> list[UserTemplate]:
    return list(
        db.scalars(
            select(UserTemplate)
            .where(UserTemplate.user_id == user_id)
            .order_by(UserTemplate.created_at.desc())
        )
    )


def get_user_template(db: Session, *, user_id: int, template_id: int) -> UserTemplate:
    template = db.scalar(
        select(UserTemplate).where(
            UserTemplate.id == template_id,
            UserTemplate.user_id == user_id,
        )
    )
    if template is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Шаблон не найден")
    return template


async def upload_template(
    db: Session,
    *,
    user: User,
    upload: UploadFile,
    name: Optional[str],
) -> UserTemplate:
    count = db.scalar(
        select(func.count())
        .select_from(UserTemplate)
        .where(UserTemplate.user_id == user.id)
    )
    if count is not None and count >= settings.template_max_count_per_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Не более {settings.template_max_count_per_user} шаблонов на пользователя",
        )

    original_filename = upload.filename or "template"
    content = await upload.read()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Пустой файл")

    if len(content) > _max_bytes():
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Максимальный размер файла — {settings.template_max_size_mb} МБ",
        )

    file_type = _detect_file_type(original_filename, content)
    display_name = _sanitize_display_name(name or Path(original_filename).stem, "Шаблон")

    template = UserTemplate(
        user_id=user.id,
        name=display_name,
        original_filename=Path(original_filename).name[:255],
        file_type=file_type,
        mime_type=MIME_BY_TYPE[file_type],
        size_bytes=len(content),
        file_data=content,
    )
    db.add(template)
    db.commit()
    db.refresh(template)
    return template


def delete_template(db: Session, *, user_id: int, template_id: int) -> None:
    template = get_user_template(db, user_id=user_id, template_id=template_id)
    db.delete(template)
    db.commit()


def rename_template(db: Session, *, user_id: int, template_id: int, name: str) -> UserTemplate:
    template = get_user_template(db, user_id=user_id, template_id=template_id)
    template.name = _sanitize_display_name(name, template.name)
    db.commit()
    db.refresh(template)
    return template
