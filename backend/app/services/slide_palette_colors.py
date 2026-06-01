from __future__ import annotations

from typing import Optional

from pptx.dml.color import RGBColor

from app.services.template_style_extractor import UserTemplateStyle

# Обязательный фон слайда
SLIDE_BACKGROUND_WHITE = RGBColor(0xFF, 0xFF, 0xFF)


def _hex_to_rgb(hex_value: str) -> RGBColor:
    cleaned = hex_value.strip().lstrip("#")
    return RGBColor(int(cleaned[0:2], 16), int(cleaned[2:4], 16), int(cleaned[4:6], 16))


def _color_int(rgb: RGBColor) -> int:
    try:
        return int(rgb)
    except TypeError:
        return (int(rgb[0]) << 16) | (int(rgb[1]) << 8) | int(rgb[2])


def _muted_from_dark(rgb: RGBColor) -> RGBColor:
    """Приглушённый текст — чуть светлее основного, без подмены акцентом."""
    value = _color_int(rgb)
    r, g, b = (value >> 16) & 0xFF, (value >> 8) & 0xFF, value & 0xFF
    return RGBColor(
        min(255, int(r + (255 - r) * 0.35)),
        min(255, int(g + (255 - g) * 0.35)),
        min(255, int(b + (255 - b) * 0.35)),
    )


def _luminance(rgb: RGBColor) -> float:
    value = _color_int(rgb)
    r, g, b = (value >> 16) & 0xFF, (value >> 8) & 0xFF, value & 0xFF
    return (0.299 * r + 0.587 * g + 0.114 * b) / 255.0


def palette_rgb(style: UserTemplateStyle, role: str) -> RGBColor:
    """
    Цвета только из анализа шаблона (palette_hex + назначенные accent/dark/card).
    Без дополнительных «контрастных» оттенков.
    """
    if role == "background":
        return SLIDE_BACKGROUND_WHITE

    if role == "accent":
        if style.accent_rgb is not None:
            return style.accent_rgb
    elif role == "dark":
        if style.dark_rgb is not None:
            return style.dark_rgb
    elif role == "card":
        if style.card_fill_rgb is not None:
            return style.card_fill_rgb
    elif role == "light":
        return SLIDE_BACKGROUND_WHITE
    elif role == "on_accent":
        if style.palette_hex:
            candidates = [_hex_to_rgb(h) for h in style.palette_hex]
            lightest = max(candidates, key=_luminance)
            if _luminance(lightest) >= 0.80:
                return lightest
        return SLIDE_BACKGROUND_WHITE
    elif role == "muted":
        if style.dark_rgb is not None:
            return _muted_from_dark(style.dark_rgb)
        if style.body_text_style.rgb is not None:
            return _muted_from_dark(style.body_text_style.rgb)

    if style.palette_hex:
        idx = {"accent": 0, "dark": 1, "card": -1, "muted": 1}.get(role, 0)
        try:
            return _hex_to_rgb(style.palette_hex[idx])
        except IndexError:
            return _hex_to_rgb(style.palette_hex[0])

    if role in ("accent", "dark", "muted"):
        return RGBColor(0x33, 0x33, 0x33)
    return SLIDE_BACKGROUND_WHITE
