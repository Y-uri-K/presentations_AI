from __future__ import annotations

import re
from typing import Any, Dict, List

from app.schemas.semantic_slides import SlideType, VISUAL_SLIDE_TYPES

_METRIC_RE = re.compile(
    r"\d+[\s,.]?\d*\s*%|\+\d|−\d|-\d|×\d|x\d|kpi|метрик|показател|рост|снижен|"
    r"анализ|аналитик|статистик|данн|dashboard|chart|график",
    re.IGNORECASE,
)
_STEP_RE = re.compile(
    r"этап|шаг|фаза|stage|step|квартал|недел|месяц|год\s*\d|q[1-4]",
    re.IGNORECASE,
)
_COMPARE_RE = re.compile(r"vs\.?|против|сравнен|до/после|альтернатив|versus", re.IGNORECASE)
_PROCESS_RE = re.compile(r"процесс|workflow|воркфлоу|pipeline|цепочк|схема работы", re.IGNORECASE)
_TABLE_RE = re.compile(r"таблиц|table|столбц|строка\s*\d", re.IGNORECASE)
_AGENDA_RE = re.compile(r"повестк|agenda|содержание|план презентации|оглавлен", re.IGNORECASE)
_PROBLEM_RE = re.compile(r"проблем|вызов|боль|pain|барьер|риск", re.IGNORECASE)
_GOALS_RE = re.compile(r"цел[ьи]|задач|mission|objective", re.IGNORECASE)
_RESULTS_RE = re.compile(r"результат|итог|вывод|достижен|impact|эффект", re.IGNORECASE)
_CARDS_RE = re.compile(r"преимуществ|функци|возможност|features|benefits|пункт", re.IGNORECASE)
_DIAGRAM_RE = re.compile(r"диаграм|график|chart|схема|архитектур|model", re.IGNORECASE)

_BULLET_ONLY_TYPES = frozenset({"problem", "goals", "conclusion"})


def _text_blob(slide: Dict[str, Any]) -> str:
    parts: List[str] = [slide.get("title") or "", slide.get("intent") or ""]
    for key, value in slide.items():
        if isinstance(value, str):
            parts.append(value)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, str):
                    parts.append(item)
                elif isinstance(item, dict):
                    parts.extend(str(v) for v in item.values() if isinstance(v, str))
        elif isinstance(value, dict):
            parts.extend(str(v) for v in value.values() if isinstance(v, str))
    return " ".join(parts).lower()


def infer_slide_type(slide: Dict[str, Any], *, position: int, total: int) -> SlideType:
    blob = _text_blob(slide)
    current = slide.get("type")

    if position == 0:
        return "title"
    if position == total - 1 and any(word in blob for word in ("спасибо", "thank", "контакт", "вопрос")):
        return "thank_you"
    if position == total - 1 and _RESULTS_RE.search(blob):
        return "conclusion"

    metrics = slide.get("metrics") or []
    if metrics or len(_METRIC_RE.findall(blob)) >= 2:
        return "kpi"
    if slide.get("table") or _TABLE_RE.search(blob):
        return "table"
    if slide.get("steps") and _PROCESS_RE.search(blob):
        return "process"
    if slide.get("steps") or len(_STEP_RE.findall(blob)) >= 2:
        return "timeline"
    if slide.get("left") and slide.get("right"):
        return "comparison"
    if _COMPARE_RE.search(blob):
        return "comparison"
    if slide.get("cards") or (_CARDS_RE.search(blob) and "•" not in blob):
        return "cards"
    if _AGENDA_RE.search(blob) or (position == 1 and slide.get("items")):
        return "agenda"
    if _PROBLEM_RE.search(blob):
        return "problem"
    if _GOALS_RE.search(blob):
        return "goals"
    if slide.get("results") or _RESULTS_RE.search(blob):
        return "results"
    if _DIAGRAM_RE.search(blob) or slide.get("type") == "diagram":
        return "diagram"
    if _PROCESS_RE.search(blob):
        return "process"

    if current in VISUAL_SLIDE_TYPES:
        return current  # type: ignore[return-value]

    # Avoid plain bullet slides: upgrade generic content
    if current in (None, "title_content", "section") or current not in VISUAL_SLIDE_TYPES:
        items = slide.get("items") or slide.get("pain_points") or slide.get("goals") or slide.get("takeaways")
        if isinstance(items, list) and len(items) >= 3:
            if _AGENDA_RE.search(blob):
                return "agenda"
            if _PROBLEM_RE.search(blob):
                return "problem"
            if _GOALS_RE.search(blob):
                return "goals"
            return "cards"
        if _METRIC_RE.search(blob):
            return "kpi"

    return current or "cards"  # type: ignore[return-value]


def apply_layout_rules(plan_slides: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    total = len(plan_slides)
    updated: List[Dict[str, Any]] = []
    seen_types: set[str] = set()

    for index, slide in enumerate(plan_slides):
        copy = dict(slide)
        new_type = infer_slide_type(copy, position=index, total=total)

        # Diversity: second agenda -> cards
        if new_type == "agenda" and "agenda" in seen_types:
            new_type = "cards"
        if (
            new_type == "kpi"
            and sum(1 for item in seen_types if item == "kpi") >= 2
            and not _METRIC_RE.search(_text_blob(copy))
        ):
            new_type = "cards"

        copy["type"] = new_type
        seen_types.add(new_type)
        updated.append(copy)

    return updated


def coerce_away_bullet_layout(slide: Dict[str, Any]) -> Dict[str, Any]:
    """Convert legacy bullet-only payloads into visual structures."""
    bullets = slide.pop("bullets", None) or slide.pop("items", None)
    if not bullets or slide.get("type") in VISUAL_SLIDE_TYPES:
        return slide

    slide_type = slide.get("type") or "cards"
    if slide_type == "agenda":
        slide["items"] = bullets[:8]
    elif slide_type == "problem":
        slide["pain_points"] = bullets[:5]
    elif slide_type == "goals":
        slide["goals"] = bullets[:5]
    elif slide_type == "conclusion":
        slide["takeaways"] = bullets[:5]
    elif slide_type == "kpi" and len(bullets) >= 2:
        slide["metrics"] = [
            {"value": b.split()[0] if b.split() else "—", "label": " ".join(b.split()[1:]) or b}
            for b in bullets[:4]
        ]
    else:
        slide["type"] = "cards"
        slide["cards"] = [{"title": f"Пункт {i + 1}", "text": text} for i, text in enumerate(bullets[:6])]
    return slide
