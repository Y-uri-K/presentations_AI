from __future__ import annotations

import logging
import re
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional, Tuple

from app.schemas.slides import PresentationSlides, SlideImageSpec
from app.services.slide_layout_selector import apply_layout_rules
from app.services.slide_payload_normalizer import normalize_slide_payload

logger = logging.getLogger(__name__)

_SECTION_RE = re.compile(r"<SECTION\b([^>]*)>(.*?)</SECTION>", re.DOTALL | re.IGNORECASE)
_IMG_RE = re.compile(
    r'<IMG\b[^>]*\bquery=["\']([^"\']+)["\']',
    re.IGNORECASE,
)
_LAYOUT_TAGS = (
    "BULLETS",
    "ICONS",
    "BOXES",
    "STATS",
    "TIMELINE",
    "CYCLE",
    "ARROWS",
    "ARROW-VERTICAL",
    "STAIRCASE",
    "PYRAMID",
    "COLUMNS",
    "COMPARE",
    "BEFORE-AFTER",
    "PROS-CONS",
    "TABLE",
    "CHART",
    "CHARTS",
)
_DIV_RE = re.compile(r"<DIV\b[^>]*>(.*?)</DIV>", re.DOTALL | re.IGNORECASE)
_H3_RE = re.compile(r"<H3\b[^>]*>(.*?)</H3>", re.DOTALL | re.IGNORECASE)
_P_RE = re.compile(r"<P\b[^>]*>(.*?)</P>", re.DOTALL | re.IGNORECASE)
_TR_RE = re.compile(r"<TR\b[^>]*>(.*?)</TR>", re.DOTALL | re.IGNORECASE)
_CELL_RE = re.compile(r"<(TH|TD)\b[^>]*>(.*?)</\1>", re.DOTALL | re.IGNORECASE)


def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _extract_xml_body(raw: str) -> str:
    text = raw.strip()
    fence = re.search(r"```(?:xml)?\s*([\s\S]*?)```", text)
    if fence:
        text = fence.group(1).strip()
    start = text.find("<PRESENTATION")
    if start == -1:
        start = text.find("<presentation")
    end = text.rfind("</PRESENTATION>")
    if end == -1:
        end = text.rfind("</presentation>")
    if start != -1 and end != -1:
        return text[start : end + len("</PRESENTATION>")]
    return text


def _parse_divs(section_inner: str) -> List[Tuple[str, str]]:
    items: List[Tuple[str, str]] = []
    for div_match in _DIV_RE.finditer(section_inner):
        block = div_match.group(1)
        headings = [_clean_text(m.group(1)) for m in _H3_RE.finditer(block)]
        paragraphs = [_clean_text(m.group(1)) for m in _P_RE.finditer(block)]
        title = headings[0] if headings else ""
        body = "\n".join(paragraphs)
        if not body and len(headings) > 1:
            body = "\n".join(headings[1:])
        if not body and title:
            body = title
        if title or body:
            items.append((title, body))
    return items


def _detect_layout_tag(section_inner: str) -> Optional[str]:
    upper = section_inner.upper()
    for tag in _LAYOUT_TAGS:
        if f"<{tag}" in upper:
            return tag
    return None


def _section_layout(attrs: str) -> str:
    match = re.search(r'\blayout=["\']([^"\']+)["\']', attrs, re.IGNORECASE)
    return (match.group(1).lower() if match else "left") or "left"


def _slide_title_from_items(items: List[Tuple[str, str]], index: int) -> str:
    if items and items[0][0]:
        return items[0][0]
    return f"Слайд {index + 1}"


def _build_image_spec(section_inner: str, layout: str) -> SlideImageSpec:
    img = _IMG_RE.search(section_inner)
    if not img:
        return SlideImageSpec(source="none")
    placement = layout if layout in ("left", "right", "vertical") else "right"
    return SlideImageSpec(
        source="generate",
        prompt=img.group(1).strip(),
        placement=placement,  # type: ignore[arg-type]
    )


def _section_to_slide_dict(
    section_inner: str,
    attrs: str,
    *,
    index: int,
) -> Dict[str, Any]:
    layout_tag = _detect_layout_tag(section_inner) or "BULLETS"
    items = _parse_divs(section_inner)
    section_layout = _section_layout(attrs)
    title = _slide_title_from_items(items, index)
    image = _build_image_spec(section_inner, section_layout)

    if layout_tag == "STATS":
        metrics = []
        for h3, p in items[:6]:
            value = h3 or "—"
            label = p or h3 or "Показатель"
            if re.search(r"\d", value) or "%" in value:
                metrics.append({"value": value, "label": label})
            else:
                metrics.append({"value": "—", "label": h3 or p or "Показатель"})
        while len(metrics) < 2:
            metrics.append({"value": "—", "label": f"Показатель {len(metrics) + 1}"})
        return {"type": "kpi", "title": title, "metrics": metrics, "image": image.model_dump()}

    if layout_tag == "TIMELINE":
        steps = [{"label": h3 or p or f"Шаг {i + 1}", "description": p if h3 else None} for i, (h3, p) in enumerate(items[:7])]
        return {"type": "timeline", "title": title, "steps": steps, "image": image.model_dump()}

    if layout_tag in ("CYCLE", "ARROWS", "ARROW-VERTICAL", "STAIRCASE", "PYRAMID"):
        steps = [{"title": h3 or f"Шаг {i + 1}", "description": p} for i, (h3, p) in enumerate(items[:6])]
        return {"type": "process", "title": title, "steps": steps, "image": image.model_dump()}

    if layout_tag == "TABLE":
        rows_data: List[List[str]] = []
        headers: List[str] = []
        for tr in _TR_RE.finditer(section_inner):
            cells = [_clean_text(m.group(2)) for m in _CELL_RE.finditer(tr.group(1))]
            if not cells:
                continue
            if not headers:
                headers = cells
            else:
                rows_data.append(cells)
        return {
            "type": "table",
            "title": title,
            "table": {"headers": headers or ["Колонка 1", "Колонка 2"], "rows": rows_data},
            "image": image.model_dump(),
        }

    if layout_tag in ("COLUMNS", "COMPARE", "BEFORE-AFTER", "PROS-CONS"):
        mid = max(1, len(items) // 2)
        left_items = items[:mid]
        right_items = items[mid:]
        return {
            "type": "comparison",
            "title": title,
            "left": {
                "heading": left_items[0][0] if left_items else "Вариант A",
                "points": [p or h3 for h3, p in left_items if (p or h3)][:5],
            },
            "right": {
                "heading": right_items[0][0] if right_items else "Вариант B",
                "points": [p or h3 for h3, p in right_items if (p or h3)][:5],
            },
            "image": image.model_dump(),
        }

    if layout_tag in ("CHART", "CHARTS"):
        points = [p or h3 for h3, p in items if (p or h3)][:4]
        return {
            "type": "diagram",
            "title": title,
            "key_points": points or ["Данные на слайде"],
            "image": image.model_dump(),
        }

    if index == 0 and len(items) <= 2:
        subtitle = items[0][1] if items else None
        return {
            "type": "title",
            "title": items[0][0] if items else title,
            "subtitle": subtitle,
            "image": image.model_dump(),
        }

    cards = []
    for i, (h3, p) in enumerate(items[:6]):
        cards.append({"title": h3 or f"Пункт {i + 1}", "text": p or h3 or "—"})
    while len(cards) < 2:
        cards.append({"title": f"Пункт {len(cards) + 1}", "text": "—"})
    return {"type": "cards", "title": title, "cards": cards, "image": image.model_dump()}


def parse_presentation_xml(raw_xml: str) -> List[Dict[str, Any]]:
    xml_body = _extract_xml_body(raw_xml)
    slides: List[Dict[str, Any]] = []

    sections = list(_SECTION_RE.finditer(xml_body))
    if sections:
        for index, match in enumerate(sections):
            slides.append(_section_to_slide_dict(match.group(2), match.group(1), index=index))
        return slides

    # Fallback: ElementTree
    try:
        wrapped = xml_body if xml_body.strip().startswith("<") else f"<root>{xml_body}</root>"
        root = ET.fromstring(wrapped)
        presentation = root if root.tag.upper() == "PRESENTATION" else root.find(".//PRESENTATION")
        if presentation is not None:
            for index, section in enumerate(presentation.findall("SECTION")):
                inner = ET.tostring(section, encoding="unicode", method="xml")
                attrs = " ".join(f'{k}="{v}"' for k, v in section.attrib.items())
                slides.append(_section_to_slide_dict(inner, attrs, index=index))
    except ET.ParseError as exc:
        logger.warning("XML ElementTree parse failed: %s", exc)

    return slides


def xml_to_presentation_slides(raw_xml: str) -> PresentationSlides:
    raw_slides = parse_presentation_xml(raw_xml)
    if not raw_slides:
        raise ValueError("В XML нет ни одного SECTION")

    # Сначала типы слайдов, затем normalize — иначе steps/table не совпадут с Pydantic.
    ruled = apply_layout_rules(raw_slides)
    normalized = [normalize_slide_payload(slide) for slide in ruled]
    return PresentationSlides.model_validate({"slides": normalized})
