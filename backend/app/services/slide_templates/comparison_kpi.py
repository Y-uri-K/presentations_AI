from __future__ import annotations

from pptx.enum.shapes import MSO_AUTO_SHAPE_TYPE
from pptx.enum.text import PP_ALIGN
from pptx.util import Emu, Inches, Pt

from app.schemas.semantic_slides import ComparisonSlide, KpiSlide, MetricItem, ResultsSlide
from app.services.slide_renderers.context import RenderContext
from app.services.slide_renderers.drawing import (
    add_card,
    add_metric_block,
    add_title,
)
from app.services.slide_renderers.layout_bounds import content_bounds_for_slide, grid_positions_in_bounds
from app.services.slide_palette_colors import palette_rgb
from app.services.slide_templates._helpers import render_with_title
from app.services.slide_templates.image_layouts import (
    render_image_comparison_stack,
    render_image_metrics_column,
)
from pptx.dml.color import RGBColor


def render_comparison(ctx: RenderContext, variant: str) -> None:
    spec: ComparisonSlide = ctx.spec  # type: ignore[assignment]
    if variant == "image_stack_top" or ctx.has_image_zone:
        render_image_comparison_stack(ctx, spec)
        return

    render_with_title(ctx)
    bounds = content_bounds_for_slide(ctx)

    if variant == "versus_center":
        mid = (bounds.left_pct + bounds.right_pct) / 2
        col_w = (mid - bounds.left_pct - 0.06)
        top = bounds.top_pct
        h = bounds.bottom_pct - top
        add_card(
            ctx,
            left_pct=bounds.left_pct,
            top_pct=top,
            width_pct=col_w,
            height_pct=h,
            heading=spec.left.heading,
            body="\n".join(f"• {p}" for p in spec.left.points[:5]),
            style="rounded",
        )
        add_card(
            ctx,
            left_pct=mid + 0.06,
            top_pct=top,
            width_pct=col_w,
            height_pct=h,
            heading=spec.right.heading,
            body="\n".join(f"• {p}" for p in spec.right.points[:5]),
            accent=True,
            style="rounded",
        )
        cx = int(ctx.slide_width * mid)
        cy = int(ctx.slide_height * (top + h / 2))
        badge = ctx.slide.shapes.add_shape(
            MSO_AUTO_SHAPE_TYPE.OVAL,
            cx - Emu(Inches(0.35)),
            cy - Emu(Inches(0.35)),
            Emu(Inches(0.7)),
            Emu(Inches(0.7)),
        )
        badge.fill.solid()
        badge.fill.fore_color.rgb = ctx.accent
        badge.line.fill.background()
        tf = badge.text_frame
        p = tf.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER
        r = p.add_run()
        r.text = "VS"
        r.font.bold = True
        r.font.size = Pt(14)
        r.font.color.rgb = palette_rgb(ctx.user_style, "on_accent")
    elif variant == "stacked_rows":
        step = (bounds.bottom_pct - bounds.top_pct) / 2
        add_card(
            ctx,
            left_pct=bounds.left_pct,
            top_pct=bounds.top_pct,
            width_pct=bounds.right_pct - bounds.left_pct,
            height_pct=step * 0.92,
            heading=spec.left.heading,
            body="\n".join(spec.left.points[:5]),
            style="flat",
        )
        add_card(
            ctx,
            left_pct=bounds.left_pct,
            top_pct=bounds.top_pct + step,
            width_pct=bounds.right_pct - bounds.left_pct,
            height_pct=step * 0.92,
            heading=spec.right.heading,
            body="\n".join(spec.right.points[:5]),
            accent=True,
            style="sidebar",
        )
    elif variant == "mirror_bars":
        mid = (bounds.left_pct + bounds.right_pct) / 2
        col_w = (mid - bounds.left_pct - 0.04)
        top = bounds.top_pct
        h = bounds.bottom_pct - top
        add_card(
            ctx,
            left_pct=bounds.left_pct,
            top_pct=top,
            width_pct=col_w,
            height_pct=h * 0.45,
            heading=spec.left.heading,
            body="\n".join(spec.left.points[:4]),
            style="flat",
        )
        add_card(
            ctx,
            left_pct=bounds.left_pct,
            top_pct=top + h * 0.52,
            width_pct=col_w,
            height_pct=h * 0.45,
            heading=spec.right.heading,
            body="\n".join(spec.right.points[:4]),
            accent=True,
            style="rounded",
        )
    else:
        mid = (bounds.left_pct + bounds.right_pct) / 2
        gap = 0.02
        col_w = (bounds.right_pct - bounds.left_pct - gap) / 2
        top = bounds.top_pct
        height = bounds.bottom_pct - top
        add_card(
            ctx,
            left_pct=bounds.left_pct,
            top_pct=top,
            width_pct=col_w,
            height_pct=height,
            heading=spec.left.heading,
            body="\n".join(f"• {p}" for p in spec.left.points[:5]),
            style="rectangle",
        )
        add_card(
            ctx,
            left_pct=mid + gap / 2,
            top_pct=top,
            width_pct=col_w,
            height_pct=height,
            heading=spec.right.heading,
            body="\n".join(f"• {p}" for p in spec.right.points[:5]),
            accent=True,
            style="rounded",
        )


def render_kpi(ctx: RenderContext, variant: str) -> None:
    spec: KpiSlide = ctx.spec  # type: ignore[assignment]
    metrics = spec.metrics[:6]
    if variant == "image_metrics_column" or ctx.has_image_zone:
        render_image_metrics_column(ctx, metrics)
        return

    render_with_title(ctx)
    bounds = content_bounds_for_slide(ctx)

    if variant == "hero_metric" and metrics:
        first = metrics[0]
        add_metric_block(
            ctx,
            left_pct=bounds.left_pct,
            top_pct=bounds.top_pct,
            width_pct=bounds.right_pct - bounds.left_pct,
            height_pct=0.28,
            value=first.value,
            label=first.label,
            note=first.note,
        )
        rest = metrics[1:5]
        gap = 0.02
        w = (bounds.right_pct - bounds.left_pct - gap * (len(rest) - 1)) / max(len(rest), 1)
        for index, metric in enumerate(rest):
            add_metric_block(
                ctx,
                left_pct=bounds.left_pct + index * (w + gap),
                top_pct=bounds.top_pct + 0.32,
                width_pct=w,
                height_pct=bounds.bottom_pct - bounds.top_pct - 0.34,
                value=metric.value,
                label=metric.label,
                note=metric.note,
            )
    elif variant == "accent_row":
        count = min(len(metrics), 4)
        gap = 0.02
        w = (bounds.right_pct - bounds.left_pct - gap * (count - 1)) / max(count, 1)
        for index, metric in enumerate(metrics[:count]):
            add_card(
                ctx,
                left_pct=bounds.left_pct + index * (w + gap),
                top_pct=bounds.top_pct,
                width_pct=w,
                height_pct=bounds.bottom_pct - bounds.top_pct,
                heading=metric.value,
                body=f"{metric.label}\n{metric.note or ''}".strip(),
                accent=index == 0,
                style="rectangle" if index % 2 else "rounded",
            )
    elif variant == "kpi_trio" and len(metrics) >= 2:
        count = min(len(metrics), 3)
        gap = 0.03
        w = (bounds.right_pct - bounds.left_pct - gap * (count - 1)) / count
        for index, metric in enumerate(metrics[:count]):
            add_metric_block(
                ctx,
                left_pct=bounds.left_pct + index * (w + gap),
                top_pct=bounds.top_pct,
                width_pct=w,
                height_pct=bounds.bottom_pct - bounds.top_pct,
                value=metric.value,
                label=metric.label,
                note=metric.note,
            )
    elif variant == "delta_cards":
        from app.services.slide_templates._helpers import render_sidebar_list

        render_sidebar_list(
            ctx,
            [
                (metric.value, f"{metric.label}\n{metric.note or ''}".strip())
                for metric in metrics[:4]
            ],
        )
    else:
        for index, (left, top, width, height) in enumerate(
            grid_positions_in_bounds(len(metrics), bounds)
        ):
            metric = metrics[index]
            add_metric_block(
                ctx,
                left_pct=left,
                top_pct=top,
                width_pct=width,
                height_pct=height,
                value=metric.value,
                label=metric.label,
                note=metric.note,
            )


def render_results(ctx: RenderContext, variant: str) -> None:
    spec: ResultsSlide = ctx.spec  # type: ignore[assignment]
    if variant == "image_metrics_column" or ctx.has_image_zone:
        from app.schemas.semantic_slides import MetricItem

        metrics = [
            MetricItem(value=r.value, label=r.label, note=r.trend) for r in spec.results[:6]
        ]
        render_image_metrics_column(ctx, metrics)
        return
    if spec.summary:
        add_title(ctx)
        from app.services.slide_renderers.drawing import add_subtitle

        add_subtitle(ctx, spec.summary, top_pct=0.20)
    else:
        render_with_title(ctx)
    kpi_spec = KpiSlide(
        type="kpi",
        title=spec.title,
        metrics=[MetricItem(value=r.value, label=r.label, note=r.trend) for r in spec.results[:6]],
        image=spec.image,
        speaker_notes=spec.speaker_notes,
    )
    kpi_ctx = RenderContext(
        slide=ctx.slide,
        spec=kpi_spec,
        slide_width=ctx.slide_width,
        slide_height=ctx.slide_height,
        user_style=ctx.user_style,
        image_bytes=ctx.image_bytes,
        slide_index=ctx.slide_index,
        layout_variant=variant if variant in ("hero_metric", "accent_row") else "metric_grid",
    )
    render_kpi(kpi_ctx, kpi_ctx.layout_variant)
