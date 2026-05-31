from __future__ import annotations

import io
from pathlib import Path

from docx import Document
from fastapi import HTTPException, status
from pypdf import PdfReader

ALLOWED_SOURCE_EXTENSIONS = {".txt", ".md", ".markdown", ".pdf", ".docx"}
TEXT_EXTENSIONS = {".txt", ".md", ".markdown"}


def _decode_text(content: bytes) -> str:
    for encoding in ("utf-8", "utf-8-sig", "cp1251", "latin-1"):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Не удалось прочитать текстовый файл",
    )


def _extract_pdf_text(content: bytes) -> str:
    reader = PdfReader(io.BytesIO(content))
    parts = []
    for page in reader.pages:
        text = page.extract_text() or ""
        if text.strip():
            parts.append(text.strip())
    return "\n\n".join(parts)


def _extract_docx_text(content: bytes) -> str:
    document = Document(io.BytesIO(content))
    parts = [paragraph.text.strip() for paragraph in document.paragraphs if paragraph.text.strip()]
    return "\n".join(parts)


def extract_source_text(*, filename: str, content: bytes) -> str:
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Пустой файл")

    extension = Path(filename).suffix.lower()
    if extension == ".doc":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Формат .doc не поддерживается. Сохраните файл как .docx",
        )
    if extension not in ALLOWED_SOURCE_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Допустимы файлы .docx, .pdf, .md, .txt",
        )

    if extension in TEXT_EXTENSIONS:
        text = _decode_text(content)
    elif extension == ".pdf":
        text = _extract_pdf_text(content)
    else:
        text = _extract_docx_text(content)

    cleaned = text.strip()
    if not cleaned:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Не удалось извлечь текст из файла {filename}",
        )
    return cleaned
