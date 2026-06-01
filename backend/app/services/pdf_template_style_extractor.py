from __future__ import annotations

import logging
from collections import Counter
from typing import List, Optional, Tuple

import fitz
from PIL import Image
from pptx.dml.color import RGBColor

from app.services.template_style_extractor import TextStyleHint, UserTemplateStyle

logger = logging.getLogger(__name__)

_PDF_RENDER_MATRIX = fitz.Matrix(1.5, 1.5)
_MAX_PAGES_FOR_TEXT = 3


def _int_to_rgb(color: int) -> RGBColor:
    return RGBColor((color >> 16) & 0xFF, (color >> 8) & 0xFF, color & 0xFF)


def _color_to_int(color: RGBColor) -> int:
    try:
        return int(color)
    except TypeError:
        return (int(color[0]) << 16) | (int(color[1]) << 8) | int(color[2])


def _span_records(doc: fitz.Document) -> List[dict]:
    records: List[dict] = []
    for page_index in range(min(len(doc), _MAX_PAGES_FOR_TEXT)):
        page = doc[page_index]
        for block in page.get_text("dict").get("blocks", []):
            if block.get("type") != 0:
                continue
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    text = (span.get("text") or "").strip()
                    if len(text) < 2:
                        continue
                    records.append(
                        {
                            "size": float(span.get("size") or 0),
                            "color": int(span.get("color") or 0),
                            "bold": bool(span.get("flags", 0) & 2**4),
                        }
                    )
    return records


def _hint_from_spans(spans: List[dict]) -> TextStyleHint:
    if not spans:
        return TextStyleHint()
    avg_size = sum(item["size"] for item in spans) / len(spans)
    common_color = Counter(item["color"] for item in spans).most_common(1)[0][0]
    bold = Counter(item["bold"] for item in spans).most_common(1)[0][0]
    return TextStyleHint(
        font_size_pt=round(avg_size, 1),
        rgb=_int_to_rgb(common_color),
        bold=bold,
    )


def _text_styles_from_records(records: List[dict]) -> Tuple[TextStyleHint, TextStyleHint]:
    if not records:
        return TextStyleHint(), TextStyleHint()

    sizes = sorted(item["size"] for item in records)
    title_cutoff = sizes[max(0, int(len(sizes) * 0.75) - 1)]
    title_spans = [item for item in records if item["size"] >= title_cutoff]
    body_spans = [item for item in records if item["size"] < title_cutoff * 0.95]
    if not body_spans:
        body_spans = [item for item in records if item not in title_spans] or records
    return _hint_from_spans(title_spans), _hint_from_spans(body_spans)


def _is_near_white(rgb: Tuple[int, int, int]) -> bool:
    return sum(rgb) >= 720


def _saturation(rgb: Tuple[int, int, int]) -> float:
    r, g, b = (channel / 255.0 for channel in rgb)
    max_c = max(r, g, b)
    min_c = min(r, g, b)
    if max_c == 0:
        return 0.0
    return (max_c - min_c) / max_c


def _palette_from_page(page: fitz.Page) -> Tuple[Optional[RGBColor], Optional[RGBColor]]:
    pixmap = page.get_pixmap(matrix=_PDF_RENDER_MATRIX, alpha=False)
    image = Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)
    pixels = [
        pixel
        for pixel in image.getdata()
        if not _is_near_white(pixel)
    ]
    if not pixels:
        return None, None

    dark_pixel = min(pixels, key=sum)
    accent_candidates = sorted(pixels, key=_saturation, reverse=True)
    accent_pixel = accent_candidates[0] if accent_candidates else dark_pixel
    return RGBColor(*accent_pixel), RGBColor(*dark_pixel)


def extract_user_template_style_from_pdf(template_bytes: bytes) -> UserTemplateStyle:
    doc = fitz.open(stream=template_bytes, filetype="pdf")
    try:
        records = _span_records(doc)
        title_style, body_style = _text_styles_from_records(records)

        accent_rgb = None
        dark_rgb = None
        light_rgb = None
        if len(doc) > 0:
            accent_rgb, dark_rgb = _palette_from_page(doc[0])
            if accent_rgb is not None:
                value = _color_to_int(accent_rgb)
                r, g, b = (value >> 16) & 0xFF, (value >> 8) & 0xFF, value & 0xFF
                light_rgb = RGBColor(
                    min(255, r + 200),
                    min(255, g + 200),
                    min(255, b + 200),
                )

        style = UserTemplateStyle(
            title_text_style=title_style,
            body_text_style=body_style,
            accent_rgb=accent_rgb,
            dark_rgb=dark_rgb,
            light_rgb=light_rgb,
        )
        logger.info(
            "Стиль PDF (палитра/шрифты): title=%s pt, body=%s pt",
            title_style.font_size_pt,
            body_style.font_size_pt,
        )
        return style
    finally:
        doc.close()
