from __future__ import annotations

from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field

AgentId = Literal["ollama", "gemini", "mimo", "polza"]
PresentationStatus = Literal["draft", "building", "ready", "failed"]


class PresentationCreateResponse(BaseModel):
    id: int
    outline: str
    agent_id: AgentId
    template_id: Optional[int] = None
    template_name: Optional[str] = None
    template_file_type: Optional[Literal["pptx", "pdf"]] = None
    source_files: List[str] = Field(default_factory=list)
    status: PresentationStatus = "draft"


class PresentationBuildRequest(BaseModel):
    """Параметры сборки PPTX."""

    generate_images: bool = Field(
        default=True,
        description="Генерировать иллюстрации через Polza AI для выбранных слайдов",
    )


class PresentationBuildResponse(BaseModel):
    id: int
    status: PresentationStatus
    error_message: Optional[str] = None
    slide_count: Optional[int] = None


class PresentationOutlineUpdateRequest(BaseModel):
    outline: str = Field(min_length=1)


class PresentationOutlineUpdateResponse(BaseModel):
    id: int
    outline: str
    title: str
    status: PresentationStatus


class PresentationStatusResponse(BaseModel):
    id: int
    status: PresentationStatus
    title: str
    outline: Optional[str] = None
    template_id: Optional[int] = None
    template_name: Optional[str] = None
    template_file_type: Optional[Literal["pptx", "pdf"]] = None
    build_stage: Optional[str] = None
    error_message: Optional[str] = None
    slide_count: Optional[int] = None
    has_download: bool = False
    created_at: datetime
    updated_at: datetime


class PresentationListItem(BaseModel):
    id: int
    title: str
    status: PresentationStatus
    template_id: Optional[int] = None
    template_name: Optional[str] = None
    template_file_type: Optional[Literal["pptx", "pdf"]] = None
    slide_count: Optional[int] = None
    has_download: bool = False
    created_at: datetime
    updated_at: datetime


class PresentationRenameRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)


class PresentationRenameResponse(BaseModel):
    presentation: PresentationListItem
    message: str = "Название обновлено"


class PresentationDeleteResponse(BaseModel):
    message: str = "Презентация удалена"
