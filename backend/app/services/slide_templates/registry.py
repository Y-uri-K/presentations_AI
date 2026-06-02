from __future__ import annotations

from typing import Dict, List

VARIANTS: Dict[str, List[str]] = {
    "cards": ["visual_grid", "hero_featured", "sidebar_list", "horizontal_strip"],
    "diagram": ["hub_grid", "two_column", "flow_chain"],
    "timeline": ["step_cards", "horizontal_line", "vertical_rail", "milestones"],
    "process": ["chevrons", "step_badges", "vertical_pipe", "funnel"],
    "comparison": ["versus_center", "split_columns", "stacked_rows", "mirror_bars"],
    "kpi": ["metric_grid", "hero_metric", "accent_row", "kpi_trio"],
    "conclusion": ["visual_stack", "numbered", "checklist"],
    "table": ["wide", "compact", "striped"],
    "agenda": ["visual_path", "vertical_list", "numbered_path"],
    "problem": ["visual_ladder", "accent_row", "visual_grid"],
    "goals": ["target_rings", "hero_featured", "visual_grid"],
    "results": ["hero_metric", "metric_grid", "accent_row"],
    "title": ["center"],
    "thank_you": ["center"],
}

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
