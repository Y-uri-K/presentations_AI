from __future__ import annotations

import io
from typing import Iterable, List, Optional, Sequence, Tuple

from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_AUTO_SHAPE_TYPE, MSO_SHAPE_TYPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Emu, Inches, Pt

from app.services.pptx_fonts import apply_font_family_preserve_to_text_frame
from app.services.slide_palette_colors import palette_rgb
from app.services.slide_renderers.context import RenderContext
from app.services.slide_renderers.layout_bounds import image_bounds_for_slide
from app.services.slide_content_density import normalize_content_text
from app.services.slide_renderers.text_frame import (
    configure_text_frame_autofit_grow,
    configure_text_frame_wrap,
)
from app.services.slide_renderers.text_layout import (
    MIN_CARD_HEIGHT_PCT,
    card_content_height_pct,
    estimate_block_height_pct,
)


def _emu_fraction(total: int, start_pct: float, end_pct: float) -> Tuple[int, int]:
    start = int(total * start_pct)
    size = int(total * (end_pct - start_pct))
    return start, max(size, Emu(Inches(0.1)))


def add_brand_accent_bar(ctx: RenderContext) -> None:
    """Верхняя акцентная полоса в духе корпоративного шаблона."""
    if "accent_top_bar" not in (ctx.user_style.key_elements or []):
        return
    accent = ctx.accent
    height = max(int(ctx.slide_height * 0.018), Emu(Inches(0.08)))
    bar = ctx.slide.shapes.add_shape(
        MSO_AUTO_SHAPE_TYPE.RECTANGLE,
        Emu(0),
        Emu(0),
        ctx.slide_width,
        height,
    )
    bar.fill.solid()
    bar.fill.fore_color.rgb = accent
    bar.line.fill.background()


def add_title(ctx: RenderContext, *, top_pct: float = 0.06, height_pct: float = 0.16) -> None:
    left, width = _emu_fraction(ctx.slide_width, 0.06, 0.94)
    top, height = _emu_fraction(ctx.slide_height, top_pct, top_pct + height_pct)
    box = ctx.slide.shapes.add_textbox(left, top, width, height)
    frame = box.text_frame
    configure_text_frame_wrap(frame, anchor=MSO_ANCHOR.TOP)
    paragraph = frame.paragraphs[0]
    paragraph.alignment = PP_ALIGN.LEFT
    run = paragraph.add_run()
    run.text = ctx.spec.title
    run.font.bold = True
    size_pt = ctx.user_style.title_text_style.font_size_pt or 32
    run.font.size = Pt(size_pt)
    run.font.color.rgb = ctx.title_color
    apply_font_family_preserve_to_text_frame(frame)


def add_subtitle(ctx: RenderContext, text: str, *, top_pct: float = 0.2) -> None:
    if not text:
        return
    left, width = _emu_fraction(ctx.slide_width, 0.06, 0.94)
    top, height = _emu_fraction(ctx.slide_height, top_pct, top_pct + 0.14)
    box = ctx.slide.shapes.add_textbox(left, top, width, height)
    frame = box.text_frame
    configure_text_frame_wrap(frame, anchor=MSO_ANCHOR.TOP)
    paragraph = frame.paragraphs[0]
    run = paragraph.add_run()
    run.text = text
    run.font.size = Pt(ctx.user_style.body_text_style.font_size_pt or 20)
    run.font.color.rgb = palette_rgb(ctx.user_style, "muted")
    apply_font_family_preserve_to_text_frame(frame)


def _fill_card_text(
    text_frame,
    *,
    heading: str,
    body: str,
    accent: bool,
    ctx: RenderContext,
) -> None:
    configure_text_frame_wrap(text_frame, anchor=MSO_ANCHOR.TOP)
    text_frame.margin_left = Pt(10)
    text_frame.margin_right = Pt(10)
    text_frame.margin_top = Pt(8)
    text_frame.margin_bottom = Pt(8)

    show_heading = heading and heading not in ("—", "-", "•") and heading != body and len(heading) < 80
    p1 = text_frame.paragraphs[0]
    p1.alignment = PP_ALIGN.LEFT
    if show_heading:
        r1 = p1.add_run()
        r1.text = heading
        r1.font.bold = True
        r1.font.size = Pt(13 if not accent else 15)
        r1.font.color.rgb = (
            palette_rgb(ctx.user_style, "on_accent") if accent else palette_rgb(ctx.user_style, "dark")
        )
        p_body = text_frame.add_paragraph()
    else:
        p_body = p1
    p_body.alignment = PP_ALIGN.LEFT
    r2 = p_body.add_run()
    r2.text = body
    r2.font.size = Pt(11 if not accent else 12)
    r2.font.color.rgb = (
        palette_rgb(ctx.user_style, "on_accent") if accent else palette_rgb(ctx.user_style, "muted")
    )
    apply_font_family_preserve_to_text_frame(text_frame)


def add_card(
    ctx: RenderContext,
    *,
    left_pct: float,
    top_pct: float,
    width_pct: float,
    height_pct: float,
    heading: str,
    body: str,
    accent: bool = False,
    style: str = "rounded",
) -> None:
    heading = normalize_content_text(heading) or ""
    body = normalize_content_text(body) or heading
    if not body or body in ("—", "-"):
        return

    need_h = card_content_height_pct(heading, body, width_pct)
    height_pct = max(height_pct, need_h)
    left, width = _emu_fraction(ctx.slide_width, left_pct, left_pct + width_pct)
    top, height = _emu_fraction(ctx.slide_height, top_pct, top_pct + height_pct)
    shape_type = MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE
    if style in ("rectangle", "flat", "sidebar"):
        shape_type = MSO_AUTO_SHAPE_TYPE.RECTANGLE

    card_left = int(left)
    card_width = int(width)
    if style == "sidebar":
        stripe_w = max(int(width * 0.04), Emu(Inches(0.06)))
        stripe = ctx.slide.shapes.add_shape(
            MSO_AUTO_SHAPE_TYPE.RECTANGLE,
            left,
            top,
            stripe_w,
            height,
        )
        stripe.fill.solid()
        stripe.fill.fore_color.rgb = ctx.accent
        stripe.line.fill.background()
        card_left = int(left) + stripe_w
        card_width = int(width) - stripe_w

    shape = ctx.slide.shapes.add_shape(shape_type, card_left, top, card_width, height)
    fill = shape.fill
    fill.solid()
    fill_rgb = None
    if accent:
        fill_rgb = ctx.accent
        fill.fore_color.rgb = fill_rgb
    elif style == "sidebar":
        fill_rgb = palette_rgb(ctx.user_style, "card")
        fill.fore_color.rgb = fill_rgb
    else:
        fill_rgb = palette_rgb(ctx.user_style, "card")
        fill.fore_color.rgb = fill_rgb
    shape.line.color.rgb = ctx.accent
    _fill_card_text(shape.text_frame, heading=heading, body=body, accent=accent, ctx=ctx)


def add_card_stack(
    ctx: RenderContext,
    *,
    left_pct: float,
    top_pct: float,
    width_pct: float,
    bottom_pct: float,
    items: Sequence[Tuple[str, str]],
    accent_first: bool = True,
    style: str = "sidebar",
    gap_pct: float = 0.014,
) -> None:
    """Вертикальный стек фигур-карточек: у каждой своя высота под полный текст."""
    visible = [(normalize_content_text(h), normalize_content_text(b)) for h, b in items]
    visible = [(h, b) for h, b in visible if b and b not in ("—", "-")]
    if not visible:
        return

    heights = [card_content_height_pct(h, b, width_pct) for h, b in visible]
    gaps = gap_pct * max(len(visible) - 1, 0)
    available = bottom_pct - top_pct
    total = sum(heights) + gaps
    if total > available and sum(heights) > 0:
        scale = max(0.5, (available - gaps) / sum(heights))
        heights = [max(MIN_CARD_HEIGHT_PCT, h * scale) for h in heights]

    y = top_pct
    for index, ((heading, body), hp) in enumerate(zip(visible, heights)):
        add_card(
            ctx,
            left_pct=left_pct,
            top_pct=y,
            width_pct=width_pct,
            height_pct=hp,
            heading=heading,
            body=body,
            accent=accent_first and index == 0,
            style=style,
        )
        y += hp + gap_pct


def add_stacked_text_block(
    ctx: RenderContext,
    *,
    left_pct: float,
    top_pct: float,
    width_pct: float,
    height_pct: float,
    items: Sequence[Tuple[str, str]],
) -> None:
    """
    Один текстовый блок на всю колонку — перенос строк без обрезки по краям карточек.
    """
    if not items:
        return
    left, width = _emu_fraction(ctx.slide_width, left_pct, left_pct + width_pct)
    top, height = _emu_fraction(ctx.slide_height, top_pct, top_pct + height_pct)
    # Минимальная высота; SHAPE_TO_FIT_TEXT расширит блок под весь текст.
    min_h = Emu(Inches(0.4))
    box = ctx.slide.shapes.add_textbox(left, top, width, max(int(height), int(min_h)))
    frame = box.text_frame
    configure_text_frame_autofit_grow(frame, anchor=MSO_ANCHOR.TOP)
    frame.margin_left = Pt(8)
    frame.margin_right = Pt(8)
    frame.margin_top = Pt(6)
    frame.margin_bottom = Pt(6)

    for index, (heading, body) in enumerate(items):
        text = normalize_content_text(body) or normalize_content_text(heading)
        if not text:
            continue
        h = (heading or "").strip()
        p = frame.paragraphs[0] if index == 0 else frame.add_paragraph()
        p.space_after = Pt(8)
        p.level = 0
        if h and h not in ("•", "—", "1", "2", "3", "4", "5") and h != text and len(h) < 50:
            r_head = p.add_run()
            r_head.text = f"{h}\n"
            r_head.font.bold = True
            r_head.font.size = Pt(11)
            r_head.font.color.rgb = palette_rgb(ctx.user_style, "dark")
        r_body = p.add_run()
        r_body.text = text
        r_body.font.size = Pt(10)
        r_body.font.color.rgb = palette_rgb(ctx.user_style, "muted")
    apply_font_family_preserve_to_text_frame(frame)


def add_metric_block(
    ctx: RenderContext,
    *,
    left_pct: float,
    top_pct: float,
    width_pct: float,
    height_pct: float,
    value: str,
    label: str,
    note: Optional[str] = None,
) -> None:
    note_text = (note or "").strip()
    block = f"{value}\n{label}" + (f"\n{note_text}" if note_text else "")
    need_h = card_content_height_pct(value, block, width_pct)
    height_pct = max(height_pct, need_h)

    left, width = _emu_fraction(ctx.slide_width, left_pct, left_pct + width_pct)
    top, height = _emu_fraction(ctx.slide_height, top_pct, top_pct + height_pct)
    shape = ctx.slide.shapes.add_shape(MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE, left, top, width, height)
    shape.fill.solid()
    shape.fill.fore_color.rgb = palette_rgb(ctx.user_style, "background")
    shape.line.color.rgb = ctx.accent

    tf = shape.text_frame
    configure_text_frame_wrap(tf, anchor=MSO_ANCHOR.TOP)
    p_val = tf.paragraphs[0]
    p_val.alignment = PP_ALIGN.CENTER
    r_val = p_val.add_run()
    r_val.text = value
    r_val.font.bold = True
    r_val.font.size = Pt(28)
    r_val.font.color.rgb = ctx.accent

    p_lbl = tf.add_paragraph()
    p_lbl.alignment = PP_ALIGN.CENTER
    r_lbl = p_lbl.add_run()
    r_lbl.text = label
    r_lbl.font.size = Pt(12)
    r_lbl.font.color.rgb = palette_rgb(ctx.user_style, "dark")

    if note:
        p_note = tf.add_paragraph()
        p_note.alignment = PP_ALIGN.CENTER
        r_note = p_note.add_run()
        r_note.text = note
        r_note.font.size = Pt(10)
        r_note.font.color.rgb = palette_rgb(ctx.user_style, "muted")
    apply_font_family_preserve_to_text_frame(tf)


def add_horizontal_timeline(
    ctx: RenderContext,
    steps: Sequence[Tuple[str, Optional[str]]],
    *,
    top_pct: float = 0.38,
) -> None:
    count = len(steps)
    if count == 0:
        return
    y_line = int(ctx.slide_height * top_pct)
    x_start = int(ctx.slide_width * 0.08)
    x_end = int(ctx.slide_width * 0.92)
    segment = (x_end - x_start) // max(count - 1, 1)

    line = ctx.slide.shapes.add_shape(
        MSO_AUTO_SHAPE_TYPE.RECTANGLE,
        x_start,
        y_line,
        x_end - x_start,
        Emu(Inches(0.03)),
    )
    line.fill.solid()
    line.fill.fore_color.rgb = ctx.accent
    line.line.fill.background()

    for index, (label, description) in enumerate(steps):
        x = x_start + segment * index
        node = ctx.slide.shapes.add_shape(
            MSO_AUTO_SHAPE_TYPE.OVAL,
            x - Emu(Inches(0.12)),
            y_line - Emu(Inches(0.12)),
            Emu(Inches(0.24)),
            Emu(Inches(0.24)),
        )
        node.fill.solid()
        node.fill.fore_color.rgb = ctx.accent
        node.line.fill.background()

        box_top = y_line + Emu(Inches(0.2))
        box = ctx.slide.shapes.add_textbox(
            x - Emu(Inches(0.9)),
            box_top,
            Emu(Inches(1.8)),
            Emu(Inches(0.9)),
        )
        tf = box.text_frame
        configure_text_frame_wrap(tf, anchor=MSO_ANCHOR.TOP)
        p = tf.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER
        r = p.add_run()
        r.text = label
        r.font.bold = True
        r.font.size = Pt(11)
        r.font.color.rgb = palette_rgb(ctx.user_style, "dark")
        if description:
            p2 = tf.add_paragraph()
            p2.alignment = PP_ALIGN.CENTER
            r2 = p2.add_run()
            r2.text = description
            r2.font.size = Pt(9)
            r2.font.color.rgb = palette_rgb(ctx.user_style, "muted")
        apply_font_family_preserve_to_text_frame(tf)


def add_process_flow(ctx: RenderContext, steps: Sequence[Tuple[str, Optional[str]]]) -> None:
    count = len(steps)
    if count == 0:
        return
    gap = 0.02
    width_each = (0.88 - gap * (count - 1)) / count
    top = 0.4
    for index, (title, description) in enumerate(steps):
        left = 0.06 + index * (width_each + gap)
        add_card(
            ctx,
            left_pct=left,
            top_pct=top,
            width_pct=width_each,
            height_pct=0.42,
            heading=title,
            body=description or "",
            accent=index == count - 1,
        )
        if index < count - 1:
            arrow_left = left + width_each + gap * 0.25
            arrow = ctx.slide.shapes.add_shape(
                MSO_AUTO_SHAPE_TYPE.RIGHT_ARROW,
                int(ctx.slide_width * arrow_left),
                int(ctx.slide_height * (top + 0.16)),
                Emu(Inches(0.35)),
                Emu(Inches(0.2)),
            )
            arrow.fill.solid()
            arrow.fill.fore_color.rgb = ctx.accent
            arrow.line.fill.background()


def add_table(
    ctx: RenderContext,
    headers: List[str],
    rows: List[List[str]],
    *,
    top_pct: float = 0.32,
) -> None:
    if not headers:
        return
    cols = len(headers)
    table_rows = 1 + len(rows)
    left, width = _emu_fraction(ctx.slide_width, 0.06, 0.94)
    top, height = _emu_fraction(ctx.slide_height, top_pct, 0.9)
    table_shape = ctx.slide.shapes.add_table(table_rows, cols, left, top, width, height)
    table = table_shape.table

    for col_index, header in enumerate(headers):
        cell = table.cell(0, col_index)
        cell.text = header
        configure_text_frame_wrap(cell.text_frame, anchor=MSO_ANCHOR.MIDDLE)
        for paragraph in cell.text_frame.paragraphs:
            for run in paragraph.runs:
                run.font.bold = True
                run.font.size = Pt(11)
                run.font.color.rgb = palette_rgb(ctx.user_style, "on_accent")
        cell.fill.solid()
        cell.fill.fore_color.rgb = ctx.accent

    for row_index, row in enumerate(rows, start=1):
        for col_index in range(cols):
            value = row[col_index] if col_index < len(row) else ""
            cell = table.cell(row_index, col_index)
            cell.text = value
            configure_text_frame_wrap(cell.text_frame, anchor=MSO_ANCHOR.TOP)
            for paragraph in cell.text_frame.paragraphs:
                for run in paragraph.runs:
                    run.font.size = Pt(10)
                    run.font.color.rgb = palette_rgb(ctx.user_style, "dark")


def add_logo_zone_marker(ctx: RenderContext) -> None:
    """Маркер зоны логотипа на титуле (по анализу шаблона)."""
    zone = ctx.user_style.title_logo_zone
    if not zone or ctx.spec.type != "title":
        return
    left_pct = 0.06 if zone == "top_left" else 0.78 if zone == "top_right" else 0.38
    left, width = _emu_fraction(ctx.slide_width, left_pct, left_pct + 0.14)
    top, height = _emu_fraction(ctx.slide_height, 0.05, 0.16)
    shape = ctx.slide.shapes.add_shape(MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE, left, top, width, height)
    shape.fill.solid()
    shape.fill.fore_color.rgb = ctx.accent
    shape.line.fill.background()
    tf = shape.text_frame
    tf.clear()
    p = tf.paragraphs[0]
    r = p.add_run()
    r.text = " "
    r.font.size = Pt(8)


def count_pictures_on_slide(slide) -> int:
    count = 0
    for shape in slide.shapes:
        try:
            if shape.shape_type == MSO_SHAPE_TYPE.PICTURE:
                count += 1
        except (AttributeError, ValueError):
            continue
    return count


def _fit_picture_size(
    image_bytes: bytes,
    box_width_emu: int,
    box_height_emu: int,
) -> tuple[int, int]:
    from PIL import Image

    with Image.open(io.BytesIO(image_bytes)) as img:
        img_w, img_h = img.size
    box_w = max(int(box_width_emu), 1)
    box_h = max(int(box_height_emu), 1)
    if img_w <= 0 or img_h <= 0:
        return box_w, box_h
    aspect = img_w / img_h
    box_aspect = box_w / box_h
    if aspect >= box_aspect:
        pic_w = box_w
        pic_h = max(1, int(box_w / aspect))
    else:
        pic_h = box_h
        pic_w = max(1, int(box_h * aspect))
    return pic_w, pic_h


def add_image_area(
    ctx: RenderContext,
    *,
    left_pct: float = 0.52,
    width_pct: float = 0.42,
    top_pct: float = 0.32,
    bottom_pct: float = 0.88,
    behind_content: bool = True,
) -> None:
    del behind_content
    from app.services.slide_renderers.image_insert import insert_slide_image_verified

    insert_slide_image_verified(ctx)


def add_slide_image(ctx: RenderContext) -> None:
    """Картинка в отдельной зоне — под текстом (z-order)."""
    add_slide_image_verified(ctx)


def add_slide_image_verified(ctx: RenderContext) -> bool:
    """Вставляет изображение после контента; возвращает True при успехе."""
    from app.services.slide_renderers.image_insert import insert_slide_image_verified

    return insert_slide_image_verified(ctx)


def grid_positions(count: int) -> Iterable[Tuple[float, float, float, float]]:
    layouts = {
        2: [(0.06, 0.34, 0.42, 0.5), (0.52, 0.34, 0.42, 0.5)],
        3: [
            (0.06, 0.34, 0.27, 0.5),
            (0.365, 0.34, 0.27, 0.5),
            (0.67, 0.34, 0.27, 0.5),
        ],
        4: [
            (0.06, 0.34, 0.42, 0.28),
            (0.52, 0.34, 0.42, 0.28),
            (0.06, 0.66, 0.42, 0.28),
            (0.52, 0.66, 0.42, 0.28),
        ],
    }
    if count in layouts:
        yield from layouts[count]
        return
    cols = 3
    rows = (count + cols - 1) // cols
    cell_w = 0.88 / cols
    cell_h = 0.55 / max(rows, 1)
    for index in range(count):
        row = index // cols
        col = index % cols
        yield (
            0.06 + col * cell_w,
            0.34 + row * cell_h,
            cell_w - 0.02,
            cell_h - 0.02,
        )
