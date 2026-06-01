from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Tuple

from app.services.slide_renderers.context import RenderContext
from app.services.slide_renderers.text_layout import (
    COLUMN_GAP_PCT,
    SLIDE_HALF_WIDTH_PCT,
    _MARGIN_LEFT_PCT,
)

TITLE_ZONE_BOTTOM_PCT = 0.26
CONTENT_TOP_PCT = 0.26
CONTENT_BOTTOM_PCT = 0.88
IMAGE_GAP_PCT = COLUMN_GAP_PCT

# Половина рабочей ширины слайда (между полями) — текст | зазор | картинка
_CONTENT_WIDTH = SLIDE_HALF_WIDTH_PCT - IMAGE_GAP_PCT / 2
_IMAGE_WIDTH = SLIDE_HALF_WIDTH_PCT - IMAGE_GAP_PCT / 2

# Вертикальная раскладка: текст сверху ~45%, картинка снизу ~45%
_VERTICAL_CONTENT_BOTTOM = 0.50
_VERTICAL_IMAGE_TOP = 0.52
_VERTICAL_IMAGE_BOTTOM = 0.90


@dataclass(frozen=True)
class ContentBounds:
    left_pct: float = 0.06
    right_pct: float = 0.94
    top_pct: float = CONTENT_TOP_PCT
    bottom_pct: float = CONTENT_BOTTOM_PCT


@dataclass(frozen=True)
class ImageBounds:
    left_pct: float
    right_pct: float
    top_pct: float
    bottom_pct: float


def _image_side(ctx: RenderContext) -> str:
    placement = getattr(ctx.spec.image, "placement", None)
    if placement in ("left", "right"):
        return placement
    return ctx.user_style.content_image_side or "right"


def content_bounds_for_slide(ctx: RenderContext) -> ContentBounds:
    if ctx.spec.type == "table":
        return ContentBounds(left_pct=0.06, right_pct=0.94, top_pct=CONTENT_TOP_PCT, bottom_pct=0.90)
    if not ctx.has_image_zone:
        return ContentBounds()

    side = _image_side(ctx)
    if side == "vertical":
        return ContentBounds(
            left_pct=_MARGIN_LEFT_PCT,
            right_pct=1.0 - _MARGIN_LEFT_PCT,
            top_pct=CONTENT_TOP_PCT,
            bottom_pct=_VERTICAL_CONTENT_BOTTOM,
        )
    if side == "left":
        return ContentBounds(
            left_pct=_MARGIN_LEFT_PCT + _IMAGE_WIDTH + IMAGE_GAP_PCT,
            right_pct=1.0 - _MARGIN_LEFT_PCT,
            top_pct=CONTENT_TOP_PCT,
            bottom_pct=CONTENT_BOTTOM_PCT,
        )
    return ContentBounds(
        left_pct=_MARGIN_LEFT_PCT,
        right_pct=_MARGIN_LEFT_PCT + _CONTENT_WIDTH,
        top_pct=CONTENT_TOP_PCT,
        bottom_pct=CONTENT_BOTTOM_PCT,
    )


def image_bounds_for_slide(ctx: RenderContext) -> ImageBounds:
    side = _image_side(ctx)
    if side == "vertical":
        return ImageBounds(
            left_pct=_MARGIN_LEFT_PCT + 0.02,
            right_pct=1.0 - _MARGIN_LEFT_PCT - 0.02,
            top_pct=_VERTICAL_IMAGE_TOP,
            bottom_pct=_VERTICAL_IMAGE_BOTTOM,
        )
    if ctx.spec.type == "diagram" and side == "left":
        return ImageBounds(
            left_pct=_MARGIN_LEFT_PCT,
            right_pct=_MARGIN_LEFT_PCT + _IMAGE_WIDTH,
            top_pct=CONTENT_TOP_PCT,
            bottom_pct=CONTENT_BOTTOM_PCT,
        )
    if side == "left":
        return ImageBounds(
            left_pct=_MARGIN_LEFT_PCT,
            right_pct=_MARGIN_LEFT_PCT + _IMAGE_WIDTH,
            top_pct=CONTENT_TOP_PCT,
            bottom_pct=CONTENT_BOTTOM_PCT,
        )
    return ImageBounds(
        left_pct=_MARGIN_LEFT_PCT + _CONTENT_WIDTH + IMAGE_GAP_PCT,
        right_pct=1.0 - _MARGIN_LEFT_PCT,
        top_pct=CONTENT_TOP_PCT,
        bottom_pct=CONTENT_BOTTOM_PCT,
    )


def grid_positions_in_bounds(
    count: int,
    bounds: ContentBounds,
) -> Iterable[Tuple[float, float, float, float]]:
    width_span = bounds.right_pct - bounds.left_pct
    height_span = bounds.bottom_pct - bounds.top_pct

    if width_span < 0.55:
        capped = min(count, max(1, int(height_span / 0.14)))
        step = height_span / capped
        for index in range(capped):
            yield (
                bounds.left_pct,
                bounds.top_pct + index * step,
                width_span,
                step * 0.95,
            )
        return

    base_layouts = {
        2: [(0.0, 0.0, 0.48, 1.0), (0.52, 0.0, 0.48, 1.0)],
        3: [(0.0, 0.0, 0.31, 1.0), (0.345, 0.0, 0.31, 1.0), (0.69, 0.0, 0.31, 1.0)],
        4: [
            (0.0, 0.0, 0.48, 0.48),
            (0.52, 0.0, 0.48, 0.48),
            (0.0, 0.52, 0.48, 0.48),
            (0.52, 0.52, 0.48, 0.48),
        ],
    }
    rel = base_layouts.get(count)
    if rel is None:
        cols = 2 if width_span < 0.5 else 3
        rows = (count + cols - 1) // cols
        rel = []
        cell_w = 0.96 / cols
        cell_h = 0.96 / max(rows, 1)
        for index in range(count):
            row = index // cols
            col = index % cols
            rel.append((col * cell_w, row * cell_h, cell_w - 0.04, cell_h - 0.04))

    for left_rel, top_rel, width_rel, height_rel in rel:
        yield (
            bounds.left_pct + left_rel * width_span,
            bounds.top_pct + top_rel * height_span,
            width_rel * width_span,
            height_rel * height_span,
        )
