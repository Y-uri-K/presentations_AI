from __future__ import annotations

import io
import logging
from typing import Literal, Optional

from PIL import Image, UnidentifiedImageError

logger = logging.getLogger(__name__)

_MIN_BYTES = 64
_MAX_EDGE_PX = 1280
_MAX_BYTES = 4 * 1024 * 1024
_WHITE = (255, 255, 255)


def _flatten_on_white(img: Image.Image) -> Image.Image:
    rgba = img.convert("RGBA")
    background = Image.new("RGB", rgba.size, _WHITE)
    background.paste(rgba, mask=rgba.split()[3])
    return background


def _save_jpeg(img: Image.Image) -> bytes:
    """JPEG RGB — наиболее стабильный формат для PowerPoint через python-pptx."""
    if img.mode != "RGB":
        img = img.convert("RGB")
    out = io.BytesIO()
    img.save(
        out,
        format="JPEG",
        quality=88,
        optimize=True,
        progressive=False,
        subsampling=2,
    )
    return out.getvalue()


def _validate_image_bytes(data: bytes, fmt: Literal["JPEG", "PNG"]) -> bool:
    if len(data) < _MIN_BYTES:
        return False
    try:
        with Image.open(io.BytesIO(data)) as probe:
            probe.verify()
        with Image.open(io.BytesIO(data)) as probe:
            probe.load()
            if fmt == "JPEG" and probe.format not in ("JPEG", "JPG", "MPO"):
                return False
        return True
    except Exception:
        return False


def normalize_image_for_pptx(
    image_bytes: bytes,
    *,
    mime_type: Optional[str] = None,
) -> Optional[bytes]:
    """
    JPEG RGB на белом фоне, ограниченный размер — совместимость с PowerPoint.
    """
    if not image_bytes or len(image_bytes) < _MIN_BYTES:
        logger.warning("Пропуск изображения: пустой буфер (%s байт)", len(image_bytes or b""))
        return None
    if len(image_bytes) > _MAX_BYTES * 2:
        logger.warning("Пропуск изображения: слишком большой файл (%s байт)", len(image_bytes))
        return None

    try:
        with Image.open(io.BytesIO(image_bytes)) as img:
            img.load()
    except UnidentifiedImageError:
        logger.warning(
            "Пропуск изображения: не распознан формат (mime=%s, %s байт)",
            mime_type,
            len(image_bytes),
        )
        return None

    img = _flatten_on_white(img)

    if max(img.size) > _MAX_EDGE_PX:
        img.thumbnail((_MAX_EDGE_PX, _MAX_EDGE_PX), Image.Resampling.LANCZOS)

    if img.width < 16 or img.height < 16:
        logger.warning("Пропуск изображения: размер %sx%s слишком мал", img.width, img.height)
        return None

    result = _save_jpeg(img)

    if len(result) > _MAX_BYTES:
        img.thumbnail((960, 540), Image.Resampling.LANCZOS)
        result = _save_jpeg(img)

    if not _validate_image_bytes(result, "JPEG"):
        logger.warning("Пропуск изображения: JPEG не прошёл проверку")
        return None

    return result
