from __future__ import annotations

from app.services.slide_renderers.context import RenderContext
from app.services.slide_renderers.drawing import add_brand_accent_bar, add_logo_zone_marker, add_slide_image
from app.services.slide_templates.dispatch import render_slide_with_template


def render_semantic_slide(ctx: RenderContext, *, insert_image: bool = True) -> None:
    if ctx.spec.type != "title":
        add_brand_accent_bar(ctx)
    else:
        add_logo_zone_marker(ctx)
    render_slide_with_template(ctx)
    if (
        insert_image
        and ctx.image_bytes
        and ctx.spec.type not in ("title", "thank_you")
    ):
        add_slide_image(ctx)


def render_semantic_slide_notes(ctx: RenderContext) -> None:
    if not ctx.spec.speaker_notes:
        return
    try:
        notes = ctx.slide.notes_slide
        if notes.notes_text_frame:
            notes.notes_text_frame.text = ctx.spec.speaker_notes
    except Exception:
        pass
