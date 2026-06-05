from __future__ import annotations

import base64
import re
from pathlib import Path
from typing import Optional

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import TemplateRating, User, UserTemplate

settings = get_settings()
_template_catalog_schema_checked = False

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


def _rating_stats_subquery():
    return (
        select(
            TemplateRating.template_id.label("template_id"),
            func.avg(TemplateRating.rating).label("rating_avg"),
            func.count(TemplateRating.id).label("rating_count"),
        )
        .group_by(TemplateRating.template_id)
        .subquery()
    )


async def _create_template_from_upload(
    db: Session,
    *,
    user: User,
    upload: UploadFile,
    name: Optional[str],
    is_public: bool,
) -> UserTemplate:
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
        is_public=is_public,
        download_count=0,
    )
    db.add(template)
    db.commit()
    db.refresh(template)
    return template


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

    return await _create_template_from_upload(
        db,
        user=user,
        upload=upload,
        name=name,
        is_public=False,
    )


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


async def upload_public_template(
    db: Session,
    *,
    user: User,
    upload: UploadFile,
    name: Optional[str],
) -> UserTemplate:
    return await _create_template_from_upload(
        db,
        user=user,
        upload=upload,
        name=name,
        is_public=True,
    )


def list_public_templates(
    db: Session,
    *,
    current_user_id: int,
    search: Optional[str] = None,
    sort: str = "new",
) -> list[dict]:
    stats = _rating_stats_subquery()
    user_rating = (
        select(TemplateRating.rating)
        .where(
            TemplateRating.template_id == UserTemplate.id,
            TemplateRating.user_id == current_user_id,
        )
        .correlate(UserTemplate)
        .scalar_subquery()
    )

    stmt = (
        select(
            UserTemplate,
            User.username.label("author_username"),
            func.coalesce(stats.c.rating_avg, 0).label("rating_avg"),
            func.coalesce(stats.c.rating_count, 0).label("rating_count"),
            user_rating.label("user_rating"),
        )
        .join(User, User.id == UserTemplate.user_id)
        .outerjoin(stats, stats.c.template_id == UserTemplate.id)
        .where(UserTemplate.is_public.is_(True))
    )

    if search and search.strip():
        stmt = stmt.where(UserTemplate.name.ilike(f"%{search.strip()}%"))

    if sort == "downloads":
        stmt = stmt.order_by(UserTemplate.download_count.desc(), UserTemplate.created_at.desc())
    elif sort == "rating":
        stmt = stmt.order_by(
            func.coalesce(stats.c.rating_avg, 0).desc(),
            func.coalesce(stats.c.rating_count, 0).desc(),
            UserTemplate.created_at.desc(),
        )
    elif sort == "name":
        stmt = stmt.order_by(UserTemplate.name.asc())
    else:
        stmt = stmt.order_by(UserTemplate.created_at.desc())

    return [
        {
            "template": template,
            "author_username": author_username,
            "rating_avg": float(rating_avg or 0),
            "rating_count": int(rating_count or 0),
            "user_rating": user_rating_value,
        }
        for template, author_username, rating_avg, rating_count, user_rating_value in db.execute(stmt)
    ]


def get_public_template(db: Session, *, template_id: int) -> UserTemplate:
    template = db.scalar(
        select(UserTemplate).where(
            UserTemplate.id == template_id,
            UserTemplate.is_public.is_(True),
        )
    )
    if template is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Шаблон не найден")
    return template


def download_public_template(db: Session, *, template_id: int) -> UserTemplate:
    template = get_public_template(db, template_id=template_id)
    template.download_count = int(template.download_count or 0) + 1
    db.add(template)
    db.commit()
    db.refresh(template)
    return template


def rate_template(db: Session, *, user_id: int, template_id: int, rating: int) -> dict:
    if rating < 1 or rating > 5:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Оценка должна быть от 1 до 5",
        )

    get_public_template(db, template_id=template_id)
    existing = db.scalar(
        select(TemplateRating).where(
            TemplateRating.template_id == template_id,
            TemplateRating.user_id == user_id,
        )
    )
    if existing is None:
        existing = TemplateRating(template_id=template_id, user_id=user_id, rating=rating)
        db.add(existing)
    else:
        existing.rating = rating

    db.commit()

    stats = db.execute(
        select(
            func.coalesce(func.avg(TemplateRating.rating), 0),
            func.count(TemplateRating.id),
        ).where(TemplateRating.template_id == template_id)
    ).one()
    return {
        "template_id": template_id,
        "rating_avg": float(stats[0] or 0),
        "rating_count": int(stats[1] or 0),
        "user_rating": rating,
    }


def get_public_template_preview(db: Session, *, template_id: int) -> dict:
    template = get_public_template(db, template_id=template_id)
    image_data_url = None
    preview_kind = "metadata"

    if template.file_type == "pdf":
        try:
            import fitz

            with fitz.open(stream=template.file_data, filetype="pdf") as document:
                if document.page_count:
                    page = document.load_page(0)
                    pixmap = page.get_pixmap(matrix=fitz.Matrix(1.4, 1.4), alpha=False)
                    image_data_url = (
                        "data:image/png;base64,"
                        + base64.b64encode(pixmap.tobytes("png")).decode("ascii")
                    )
                    preview_kind = "image"
        except Exception:
            image_data_url = None
    elif template.file_type == "pptx":
        preview_kind = "office"

    return {
        "template_id": template.id,
        "name": template.name,
        "file_type": template.file_type,
        "original_filename": template.original_filename,
        "size_bytes": template.size_bytes,
        "download_count": int(template.download_count or 0),
        "preview_kind": preview_kind,
        "image_data_url": image_data_url,
    }


def ensure_template_catalog_schema(db: Session) -> None:
    global _template_catalog_schema_checked

    if _template_catalog_schema_checked:
        return
    if db.bind is None or db.bind.dialect.name != "mysql":
        _template_catalog_schema_checked = True
        return

    has_is_public = db.scalar(
        text(
            """
            SELECT COUNT(*)
            FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = 'user_templates'
              AND COLUMN_NAME = 'is_public'
            """
        )
    )
    if not has_is_public:
        db.execute(
            text("ALTER TABLE user_templates ADD COLUMN is_public TINYINT(1) NOT NULL DEFAULT 0")
        )

    has_download_count = db.scalar(
        text(
            """
            SELECT COUNT(*)
            FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = 'user_templates'
              AND COLUMN_NAME = 'download_count'
            """
        )
    )
    if not has_download_count:
        db.execute(
            text(
                "ALTER TABLE user_templates "
                "ADD COLUMN download_count BIGINT UNSIGNED NOT NULL DEFAULT 0"
            )
        )

    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS template_ratings (
              id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
              template_id BIGINT UNSIGNED NOT NULL,
              user_id BIGINT UNSIGNED NOT NULL,
              rating TINYINT UNSIGNED NOT NULL,
              created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
              updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
              PRIMARY KEY (id),
              UNIQUE KEY uq_template_ratings_template_user (template_id, user_id),
              KEY idx_template_ratings_template_id (template_id),
              KEY idx_template_ratings_user_id (user_id),
              CONSTRAINT fk_template_ratings_template
                FOREIGN KEY (template_id) REFERENCES user_templates (id) ON DELETE CASCADE,
              CONSTRAINT fk_template_ratings_user
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
              CONSTRAINT chk_template_ratings_rating CHECK (rating BETWEEN 1 AND 5)
            ) ENGINE=InnoDB
              DEFAULT CHARSET=utf8mb4
              COLLATE=utf8mb4_unicode_ci
            """
        )
    )
    db.commit()
    _template_catalog_schema_checked = True
