from __future__ import annotations

from datetime import datetime
from typing import Literal

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
