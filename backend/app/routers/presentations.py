from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Body, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.content_disposition import attachment_content_disposition
from app.core.deps import get_current_user
from app.database import get_db
from app.models import User
from app.schemas.presentations import (
    PresentationBuildRequest,
    PresentationBuildResponse,
    PresentationCreateResponse,
    PresentationOutlineUpdateRequest,
    PresentationOutlineUpdateResponse,
    PresentationStatusResponse,
)
from app.services import presentation_build_service as build_service
from app.services import presentation_service as presentations

router = APIRouter(prefix="/api/presentations", tags=["presentations"])


def _slide_count(presentation) -> Optional[int]:
    if not presentation.slides_json:
        return None
    slides = presentation.slides_json.get("slides")
    if isinstance(slides, list):
        return len(slides)
    return None


@router.post("/create", response_model=PresentationCreateResponse)
async def create_presentation(
    prompt: str = Form(default=""),
    agent_id: Optional[str] = Form(default=None),
    template_id: Optional[int] = Form(default=None),
    source_files: List[UploadFile] = File(default=[]),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    uploads = [item for item in source_files if item.filename]
    result = await presentations.create_presentation_outline(
        db,
        user=current_user,
        prompt=prompt,
        agent_id=agent_id,
        template_id=template_id,
        source_files=uploads,
    )
    return PresentationCreateResponse(**result)


@router.patch("/{presentation_id}/outline", response_model=PresentationOutlineUpdateResponse)
async def update_presentation_outline(
    presentation_id: int,
    payload: PresentationOutlineUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    presentation = presentations.update_presentation_outline(
        db,
        user=current_user,
        presentation_id=presentation_id,
        outline=payload.outline,
    )
    return PresentationOutlineUpdateResponse(
        id=presentation.id,
        outline=presentation.outline,
        title=presentation.title,
        status=presentation.status,
    )


@router.post("/{presentation_id}/build", response_model=PresentationBuildResponse)
async def build_presentation(
    presentation_id: int,
    background_tasks: BackgroundTasks,
    payload: PresentationBuildRequest = Body(default_factory=PresentationBuildRequest),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    presentation = build_service.get_user_presentation(
        db,
        user_id=current_user.id,
        presentation_id=presentation_id,
    )
    if presentation.template_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Выберите шаблон перед сборкой презентации",
        )
    if presentation.status == "building":
        return PresentationBuildResponse(
            id=presentation.id,
            status=presentation.status,
            error_message=None,
            slide_count=_slide_count(presentation),
        )

    presentation.status = "building"
    presentation.error_message = None
    presentation.build_stage = "queued"
    db.commit()

    background_tasks.add_task(
        build_service.run_build_in_background,
        presentation_id=presentation_id,
        user_id=current_user.id,
        generate_images=payload.generate_images,
    )

    return PresentationBuildResponse(
        id=presentation.id,
        status="building",
        error_message=None,
        slide_count=_slide_count(presentation),
    )


@router.get("/{presentation_id}", response_model=PresentationStatusResponse)
async def get_presentation_status(
    presentation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    presentation = build_service.get_user_presentation(
        db,
        user_id=current_user.id,
        presentation_id=presentation_id,
    )
    return PresentationStatusResponse(
        id=presentation.id,
        status=presentation.status,
        title=presentation.title,
        outline=presentation.outline,
        template_id=presentation.template_id,
        build_stage=presentation.build_stage,
        error_message=presentation.error_message,
        slide_count=_slide_count(presentation),
        has_download=bool(presentation.pptx_data),
        created_at=presentation.created_at,
        updated_at=presentation.updated_at,
    )


@router.get("/{presentation_id}/download")
async def download_presentation(
    presentation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    presentation = build_service.get_user_presentation(
        db,
        user_id=current_user.id,
        presentation_id=presentation_id,
    )
    if presentation.status != "ready" or not presentation.pptx_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Файл презентации ещё не готов",
        )

    filename = f"{presentation.title.strip() or 'presentation'}.pptx"

    return Response(
        content=presentation.pptx_data,
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        headers={"Content-Disposition": attachment_content_disposition(filename)},
    )
