from __future__ import annotations

from typing import List, Optional

from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.content_disposition import attachment_content_disposition, inline_content_disposition
from app.core.public_url import build_public_api_url
from app.core.deps import get_current_user
from app.database import get_db
from app.models import User
from app.schemas.templates import (
    PublicTemplateListItem,
    TemplateDeleteResponse,
    TemplateListItem,
    TemplatePreviewResponse,
    TemplateRatingRequest,
    TemplateRatingResponse,
    TemplateRenameRequest,
    TemplateRenameResponse,
    TemplateUploadResponse,
)
from app.services import template_service as templates

router = APIRouter(prefix="/api/templates", tags=["templates"])
settings = get_settings()


@router.get("", response_model=List[TemplateListItem])
def list_templates(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    items = templates.list_user_templates(db, current_user.id)
    return [TemplateListItem.model_validate(item) for item in items]


@router.get("/public", response_model=List[PublicTemplateListItem])
def list_public_templates(
    search: Optional[str] = None,
    sort: str = "new",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rows = templates.list_public_templates(
        db,
        current_user_id=current_user.id,
        search=search,
        sort=sort,
    )
    return [
        PublicTemplateListItem(
            id=row["template"].id,
            name=row["template"].name,
            original_filename=row["template"].original_filename,
            file_type=row["template"].file_type,
            mime_type=row["template"].mime_type,
            size_bytes=row["template"].size_bytes,
            created_at=row["template"].created_at,
            author_username=row["author_username"],
            download_count=int(row["template"].download_count or 0),
            rating_avg=row["rating_avg"],
            rating_count=row["rating_count"],
            user_rating=row["user_rating"],
        )
        for row in rows
    ]


@router.post("/upload", response_model=TemplateUploadResponse)
async def upload_template(
    file: UploadFile = File(...),
    name: Optional[str] = Form(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    template = await templates.upload_template(
        db,
        user=current_user,
        upload=file,
        name=name,
    )
    return TemplateUploadResponse(template=TemplateListItem.model_validate(template))


@router.post("/public/upload", response_model=PublicTemplateListItem)
async def upload_public_template(
    file: UploadFile = File(...),
    name: Optional[str] = Form(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    template = await templates.upload_public_template(
        db,
        user=current_user,
        upload=file,
        name=name,
    )
    return PublicTemplateListItem(
        id=template.id,
        name=template.name,
        original_filename=template.original_filename,
        file_type=template.file_type,
        mime_type=template.mime_type,
        size_bytes=template.size_bytes,
        created_at=template.created_at,
        author_username=current_user.username,
        download_count=int(template.download_count or 0),
        rating_avg=0,
        rating_count=0,
        user_rating=None,
    )


@router.get("/{template_id}/download")
def download_template(
    template_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    template = templates.get_user_template(
        db,
        user_id=current_user.id,
        template_id=template_id,
    )
    headers = {
        "Content-Disposition": attachment_content_disposition(template.original_filename),
    }
    return Response(
        content=template.file_data,
        media_type=template.mime_type,
        headers=headers,
    )


@router.get("/public/{template_id}/download")
def download_public_template(
    template_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    template = templates.download_public_template(db, template_id=template_id)
    headers = {
        "Content-Disposition": attachment_content_disposition(template.original_filename),
    }
    return Response(
        content=template.file_data,
        media_type=template.mime_type,
        headers=headers,
    )


@router.get("/public/{template_id}/view")
def view_public_template(
    template_id: int,
    db: Session = Depends(get_db),
):
    template = templates.get_public_template(db, template_id=template_id)
    headers = {
        "Content-Disposition": inline_content_disposition(template.original_filename),
        "Cache-Control": "public, max-age=3600",
    }
    return Response(
        content=template.file_data,
        media_type=template.mime_type,
        headers=headers,
    )


@router.put("/public/{template_id}/rating", response_model=TemplateRatingResponse)
def rate_public_template(
    template_id: int,
    payload: TemplateRatingRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    result = templates.rate_template(
        db,
        user_id=current_user.id,
        template_id=template_id,
        rating=payload.rating,
    )
    return TemplateRatingResponse(**result)


@router.get("/public/{template_id}/preview", response_model=TemplatePreviewResponse)
def preview_public_template(
    template_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    preview = templates.get_public_template_preview(db, template_id=template_id)
    if preview["file_type"] == "pptx" and preview["preview_kind"] == "office":
        file_view_url = build_public_api_url(
            settings,
            request,
            f"/api/templates/public/{template_id}/view",
        )
        preview["file_view_url"] = file_view_url
        preview["office_viewer_url"] = (
            "https://view.officeapps.live.com/op/embed.aspx?src="
            + quote(file_view_url, safe="")
        )
    return TemplatePreviewResponse(**preview)


@router.patch("/{template_id}", response_model=TemplateRenameResponse)
def rename_template(
    template_id: int,
    payload: TemplateRenameRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    template = templates.rename_template(
        db,
        user_id=current_user.id,
        template_id=template_id,
        name=payload.name,
    )
    return TemplateRenameResponse(template=TemplateListItem.model_validate(template))


@router.delete("/{template_id}", response_model=TemplateDeleteResponse)
def delete_template(
    template_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    templates.delete_template(db, user_id=current_user.id, template_id=template_id)
    return TemplateDeleteResponse()
