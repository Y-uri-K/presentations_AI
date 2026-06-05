from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

TemplateFileType = Literal["pptx", "pdf"]


class TemplateListItem(BaseModel):
    id: int
    name: str
    original_filename: str
    file_type: TemplateFileType
    mime_type: str
    size_bytes: int
    created_at: datetime

    model_config = {"from_attributes": True}


class TemplateUploadResponse(BaseModel):
    template: TemplateListItem
    message: str = "Шаблон загружен"


class TemplateDeleteResponse(BaseModel):
    message: str = "Шаблон удалён"


class TemplateRenameRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class TemplateRenameResponse(BaseModel):
    template: TemplateListItem
    message: str = "Название обновлено"


class PublicTemplateListItem(BaseModel):
    id: int
    name: str
    original_filename: str
    file_type: TemplateFileType
    mime_type: str
    size_bytes: int
    created_at: datetime
    author_username: str
    download_count: int = 0
    rating_avg: float = 0
    rating_count: int = 0
    user_rating: Optional[int] = None


class TemplateRatingRequest(BaseModel):
    rating: int = Field(ge=1, le=5)


class TemplateRatingResponse(BaseModel):
    template_id: int
    rating_avg: float
    rating_count: int
    user_rating: int
    message: str = "Оценка сохранена"


class TemplatePreviewResponse(BaseModel):
    template_id: int
    name: str
    file_type: TemplateFileType
    original_filename: str
    size_bytes: int
    download_count: int
    preview_kind: Literal["image", "metadata", "office"]
    image_data_url: Optional[str] = None
    file_view_url: Optional[str] = None
    office_viewer_url: Optional[str] = None
