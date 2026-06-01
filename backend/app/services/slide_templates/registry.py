from __future__ import annotations

from typing import Dict, List

VARIANTS: Dict[str, List[str]] = {
    "cards": ["grid", "featured", "horizontal_strip", "sidebar_list", "mosaic", "staggered"],
    "diagram": ["stacked", "two_column", "hub_grid", "callout_lead", "pyramid", "flow_chain"],
    "timeline": ["horizontal_line", "vertical_rail", "step_cards", "milestones"],
    "process": ["chevrons", "vertical_pipe", "step_badges", "funnel"],
    "comparison": ["split_columns", "versus_center", "stacked_rows", "mirror_bars"],
    "kpi": ["metric_grid", "hero_metric", "accent_row", "kpi_trio", "delta_cards"],
    "conclusion": ["stack", "full_banners", "numbered", "checklist"],
    "table": ["wide", "compact", "striped", "key_column"],
    "agenda": ["grid", "vertical_list", "numbered_path"],
    "problem": ["grid", "accent_row", "severity_ladder"],
    "goals": ["grid", "featured", "target_rings"],
    "results": ["metric_grid", "hero_metric", "trend_row"],
    "title": ["center"],
    "thank_you": ["center"],
}

# Макеты только для слайдов с иллюстрацией — узкая колонка текста, без захода на картинку
IMAGE_VARIANTS: Dict[str, List[str]] = {
    "cards": ["image_column"],
    "diagram": ["image_visual_split"],
    "timeline": ["image_column"],
    "process": ["image_column"],
    "comparison": ["image_stack_top"],
    "kpi": ["image_metrics_column"],
    "results": ["image_metrics_column"],
    "agenda": ["image_column"],
    "problem": ["image_column"],
    "goals": ["image_column"],
    "conclusion": ["image_column"],
}


class SlideVariantPicker:
    """Выбирает визуальный шаблон; для слайдов с картинкой — отдельный набор макетов."""

    def __init__(self) -> None:
        self._last_by_type: Dict[str, str] = {}
        self._used_global: set[str] = set()

    def pick(self, slide_type: str, slide_index: int, *, has_image: bool = False) -> str:
        if has_image:
            options = IMAGE_VARIANTS.get(slide_type, ["image_column"])
        else:
            options = VARIANTS.get(slide_type, ["default"])
        if not options:
            return "image_column" if has_image else "default"
        offset = sum(ord(c) for c in slide_type) % len(options)
        choice = options[(slide_index + offset) % len(options)]
        if len(options) > 1 and self._last_by_type.get(slide_type) == choice:
            choice = options[(slide_index + offset + 1) % len(options)]
        if len(options) > 2 and choice in self._used_global:
            for candidate in options:
                if candidate != self._last_by_type.get(slide_type) and candidate not in self._used_global:
                    choice = candidate
                    break
        self._last_by_type[slide_type] = choice
        self._used_global.add(choice)
        return choice
