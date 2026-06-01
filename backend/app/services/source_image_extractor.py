from __future__ import annotations

import io
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

import fitz
from fastapi import HTTPException, status


@dataclass(frozen=True)
class ExtractedImage:
    ref: str
    source_filename: str
    index: int
    content: bytes
    mime_type: str


def _guess_mime(data: bytes) -> str:
    if data.startswith(b"\x89PNG"):
        return "image/png"
    if data.startswith(b"\xff\xd8"):
        return "image/jpeg"
    if data.startswith(b"GIF"):
        return "image/gif"
    if data.startswith(b"RIFF") and b"WEBP" in data[:16]:
        return "image/webp"
    return "image/png"


def _extract_pdf_images(filename: str, content: bytes) -> List[ExtractedImage]:
    images: List[ExtractedImage] = []
    doc = fitz.open(stream=content, filetype="pdf")
    try:
        index = 0
        for page_num in range(len(doc)):
            page = doc[page_num]
            for img_info in page.get_images(full=True):
                xref = img_info[0]
                try:
                    base = doc.extract_image(xref)
                except Exception:
                    continue
                img_bytes = base.get("image")
                if not img_bytes or len(img_bytes) < 1024:
                    continue
                mime = base.get("ext", "png")
                mime_type = f"image/{mime}" if mime else _guess_mime(img_bytes)
                ref = f"{filename}:{index}"
                images.append(
                    ExtractedImage(
                        ref=ref,
                        source_filename=filename,
                        index=index,
                        content=img_bytes,
                        mime_type=mime_type,
                    )
                )
                index += 1
    finally:
        doc.close()
    return images


def _extract_docx_images(filename: str, content: bytes) -> List[ExtractedImage]:
    images: List[ExtractedImage] = []
    index = 0
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        media_files = sorted(
            name for name in archive.namelist() if name.startswith("word/media/")
        )
        for media_path in media_files:
            if media_path.endswith("/"):
                continue
            img_bytes = archive.read(media_path)
            if len(img_bytes) < 1024:
                continue
            ref = f"{filename}:{index}"
            images.append(
                ExtractedImage(
                    ref=ref,
                    source_filename=filename,
                    index=index,
                    content=img_bytes,
                    mime_type=_guess_mime(img_bytes),
                )
            )
            index += 1
    return images


def extract_images_from_sources(
    sources: List[tuple[str, bytes]],
) -> Dict[str, ExtractedImage]:
    by_ref: Dict[str, ExtractedImage] = {}
    for filename, content in sources:
        extension = Path(filename).suffix.lower()
        extracted: List[ExtractedImage] = []
        if extension == ".pdf":
            extracted = _extract_pdf_images(filename, content)
        elif extension == ".docx":
            extracted = _extract_docx_images(filename, content)
        else:
            continue
        for image in extracted:
            by_ref[image.ref] = image
    return by_ref


def list_available_image_refs(sources: List[tuple[str, bytes]]) -> List[str]:
    return list(extract_images_from_sources(sources).keys())


def resolve_material_image(
    material_ref: str,
    by_ref: Dict[str, ExtractedImage],
) -> ExtractedImage:
    if material_ref in by_ref:
        return by_ref[material_ref]

    if ":" not in material_ref:
        matches = [img for ref, img in by_ref.items() if ref.startswith(f"{material_ref}:")]
        if len(matches) == 1:
            return matches[0]
        if matches:
            return matches[0]

    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail=f"Изображение «{material_ref}» не найдено в материалах",
    )
