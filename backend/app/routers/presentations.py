from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models import User
from app.schemas.presentations import PresentationCreateResponse
from app.services import presentation_service as presentations

router = APIRouter(prefix="/api/presentations", tags=["presentations"])


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
