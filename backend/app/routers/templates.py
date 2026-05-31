from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models import User
from app.schemas.templates import (
    TemplateDeleteResponse,
    TemplateListItem,
    TemplateRenameRequest,
    TemplateRenameResponse,
    TemplateUploadResponse,
)
from app.services import template_service as templates

router = APIRouter(prefix="/api/templates", tags=["templates"])


@router.get("", response_model=List[TemplateListItem])
def list_templates(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    items = templates.list_user_templates(db, current_user.id)
    return [TemplateListItem.model_validate(item) for item in items]


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
        "Content-Disposition": f'attachment; filename="{template.original_filename}"',
    }
    return Response(
        content=template.file_data,
        media_type=template.mime_type,
        headers=headers,
    )


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
