from __future__ import annotations

import json
import logging
import re
from typing import List, Optional

from pptx.dml.color import RGBColor

from app.ai.registry import chat_with_agent_resilient
from app.ai.types import ChatMessage
from app.config import get_settings
from app.schemas.template_blueprint import TemplateCatalog
from app.services.template_geometry_analyzer import TemplateGeometryReport, geometry_for_polza
from app.services.template_slide_inspector import SlideStyleSample, dominant_colors_from_samples
from app.services.template_palette import apply_palette_to_style
from app.services.template_style_extractor import TextStyleHint, UserTemplateStyle

logger = logging.getLogger(__name__)
settings = get_settings()

_JSON_RE = re.compile(r"\{[\s\S]*\}")


def _hex_to_rgb(value: Optional[str]) -> Optional[RGBColor]:
    if not value:
        return None
    cleaned = value.strip().lstrip("#")
    if len(cleaned) != 6:
        return None
    try:
        return RGBColor(int(cleaned[0:2], 16), int(cleaned[2:4], 16), int(cleaned[4:6], 16))
    except ValueError:
        return None


def _samples_payload(samples: List[SlideStyleSample]) -> str:
    payload = []
    for sample in samples:
        payload.append(
            {
                "slide": sample.index,
                "background": sample.background_hex,
                "accent_colors": sample.accent_colors,
                "shapes": sample.shape_kinds,
                "background_image": sample.has_background_image,
                "title_pt": sample.title_size_pt,
                "body_pt": sample.body_size_pt,
            }
        )
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _catalog_payload(catalog: TemplateCatalog) -> str:
    payload = []
    for slide in catalog.slides:
        payload.append(
            {
                "template_key": slide.template_key,
                "slide_type": slide.slide_type,
                "layout_name": slide.layout_name,
                "slots": len(slide.content_slots),
                "card_slots": slide.card_slots,
                "has_table": slide.has_table,
                "has_timeline": slide.has_timeline,
                "has_picture": slide.has_picture,
            }
        )
    return json.dumps(payload, ensure_ascii=False, indent=2)


async def analyze_template_style_with_ai(
    samples: List[SlideStyleSample],
    base: UserTemplateStyle,
    *,
    catalog: TemplateCatalog | None = None,
    geometry: TemplateGeometryReport | None = None,
) -> UserTemplateStyle:
    """AI-анализ стиля шаблона (по умолчанию MiMo, без автоматического Polza)."""
    if not samples:
        return base

    accent_guess, dark_guess, light_guess = dominant_colors_from_samples(samples)
    palette_line = ", ".join(base.palette_hex) if base.palette_hex else "—"
    catalog_block = ""
    if catalog is not None:
        catalog_block = f"\nСтруктура макетов шаблона:\n{_catalog_payload(catalog)}\n"

    geometry_block = ""
    if geometry is not None:
        geometry_block = f"\nГеометрия и типы фигур (важно — титульный слайд 1):\n{geometry_for_polza(geometry)}\n"

    prompt = f"""Проанализируй стиль корпоративного шаблона PowerPoint по данным до {len(samples)} слайдов.
Определи: акцентный цвет, цвет текста, светлый фон, шрифт, размеры заголовка и body, заливку карточек.
Особое внимание слайду 1 (титул): логотип, hero-картинка, акцентная полоса, расположение заголовка.
Учти типы фигур и схемы: карточки, timeline, стрелки/chevron, волны-линии, таблицы, диаграммы.
Не копируй слайды — только стиль для новой презентации в том же духе.

Данные слайдов (эвристика):
{_samples_payload(samples)}
{catalog_block}{geometry_block}
Подсказка цветов: accent={accent_guess}, dark={dark_guess}, light={light_guess}
ОБЯЗАТЕЛЬНО выбери accent_hex, dark_hex, light_hex, card_fill_hex ТОЛЬКО из палитры шаблона:
[{palette_line}]

Ответь ТОЛЬКО JSON без markdown:
{{
  "accent_hex": "#RRGGBB",
  "dark_hex": "#RRGGBB",
  "light_hex": "#RRGGBB",
  "card_fill_hex": "#RRGGBB",
  "font_family": "название шрифта",
  "title_size_pt": 32,
  "body_size_pt": 18,
  "use_template_background_image": true,
  "key_elements": ["accent_top_bar", "rounded_cards", "timeline_line"],
  "title_layout_pattern": "title_center|title_hero_right|title_hero_left|title_logo_top",
  "content_image_side": "left|right",
  "diagram_schemes": ["card_grid", "horizontal_timeline", "chevron_process"]
}}"""

    agent_id = settings.presentation_default_agent or "mimo"
    try:
        raw = await chat_with_agent_resilient(
            agent_id,
            [ChatMessage(role="user", content=prompt)],
        )
        match = _JSON_RE.search(raw)
        if not match:
            logger.warning("Анализ шаблона (%s): JSON не найден в ответе", agent_id)
            return base
        data = json.loads(match.group(0))
    except Exception as exc:
        logger.warning("Анализ шаблона (%s) не удался: %s", agent_id, exc)
        return base

    def _from_palette(key: str, fallback: Optional[RGBColor]) -> Optional[RGBColor]:
        raw = data.get(key)
        if isinstance(raw, str) and raw.upper() in {h.upper() for h in base.palette_hex}:
            return _hex_to_rgb(raw)
        if isinstance(raw, str):
            parsed = _hex_to_rgb(raw)
            if parsed is not None:
                return parsed
        return fallback

    accent = _from_palette("accent_hex", base.accent_rgb)
    dark = _from_palette("dark_hex", base.dark_rgb)
    light = _from_palette("light_hex", base.light_rgb)
    card_fill = _from_palette("card_fill_hex", base.card_fill_rgb)

    title_pt = data.get("title_size_pt")
    body_pt = data.get("body_size_pt")
    font_family = data.get("font_family") or base.font_family

    raw_elements = data.get("key_elements")
    key_elements: List[str] = []
    if isinstance(raw_elements, list):
        key_elements = [str(item) for item in raw_elements if item]
    if not key_elements:
        key_elements = list(base.key_elements) if base.key_elements else ["accent_top_bar", "rounded_cards"]

    title_pattern = data.get("title_layout_pattern") or base.title_layout_pattern
    content_side = data.get("content_image_side") or base.content_image_side
    if content_side not in ("left", "right"):
        content_side = base.content_image_side

    raw_schemes = data.get("diagram_schemes")
    diagram_schemes: List[str] = list(base.diagram_schemes)
    if isinstance(raw_schemes, list):
        diagram_schemes = [str(item) for item in raw_schemes if item]

    merged = UserTemplateStyle(
        theme_files=base.theme_files,
        title_text_style=TextStyleHint(
            font_size_pt=float(title_pt) if title_pt else base.title_text_style.font_size_pt,
            rgb=accent or base.title_text_style.rgb,
            bold=base.title_text_style.bold,
        ),
        body_text_style=TextStyleHint(
            font_size_pt=float(body_pt) if body_pt else base.body_text_style.font_size_pt,
            rgb=dark or base.body_text_style.rgb,
            bold=base.body_text_style.bold,
        ),
        accent_rgb=accent,
        dark_rgb=dark,
        light_rgb=light,
        font_family=font_family,
        card_fill_rgb=card_fill,
        background_image=base.background_image if data.get("use_template_background_image", True) else None,
        key_elements=key_elements,
        title_layout_pattern=str(title_pattern),
        title_logo_zone=base.title_logo_zone,
        title_hero_mode=base.title_hero_mode,
        content_image_side=content_side,
        diagram_schemes=diagram_schemes,
        shape_type_counts=dict(base.shape_type_counts),
    )
    merged.palette_hex = base.palette_hex
    merged = apply_palette_to_style(merged, base.palette_hex)

    logger.info(
        "Анализ шаблона OK (%s): палитра=%s, accent=%s, font=%s",
        agent_id,
        ", ".join(merged.palette_hex[:6]),
        _rgb_to_hex(merged.accent_rgb) if merged.accent_rgb else "—",
        font_family,
    )
    return merged


async def analyze_template_style_with_polza(
    samples: List[SlideStyleSample],
    base: UserTemplateStyle,
    *,
    catalog: TemplateCatalog | None = None,
    geometry: TemplateGeometryReport | None = None,
) -> UserTemplateStyle:
    """Обратная совместимость — фактически MiMo + fallback."""
    return await analyze_template_style_with_ai(
        samples, base, catalog=catalog, geometry=geometry
    )


def _rgb_to_hex(rgb: Optional[RGBColor]) -> Optional[str]:
    if rgb is None:
        return None
    try:
        value = int(rgb)
    except TypeError:
        value = (int(rgb[0]) << 16) | (int(rgb[1]) << 8) | int(rgb[2])
    return f"#{value:06X}"


# Обратная совместимость
async def analyze_template_style_with_agent(
    agent_id: str,
    samples: List[SlideStyleSample],
    base: UserTemplateStyle,
) -> UserTemplateStyle:
    del agent_id
    return await analyze_template_style_with_polza(samples, base)
