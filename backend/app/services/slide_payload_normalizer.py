from __future__ import annotations

from typing import Any, Dict, List, Optional


def _as_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value).strip() or default


def _as_str_list(value: Any, *, max_items: int = 8) -> List[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    if isinstance(value, list):
        result: List[str] = []
        for item in value:
            if isinstance(item, str) and item.strip():
                result.append(item.strip())
            elif isinstance(item, dict):
                text = (
                    item.get("text")
                    or item.get("label")
                    or item.get("title")
                    or item.get("value")
                    or item.get("name")
                )
                if text:
                    result.append(_as_str(text))
            elif item is not None:
                result.append(str(item))
            if len(result) >= max_items:
                break
        return result
    return []


def _comparison_side(raw: Any, *, default_heading: str) -> Dict[str, Any]:
    if isinstance(raw, dict):
        return {
            "heading": _as_str(raw.get("heading") or raw.get("title") or default_heading, default_heading),
            "points": _as_str_list(raw.get("points") or raw.get("items") or raw.get("bullets"), max_items=5),
        }
    points = _as_str_list(raw, max_items=5)
    return {"heading": default_heading, "points": points}


def _ensure_image(slide: Dict[str, Any]) -> None:
    image = slide.get("image")
    if not isinstance(image, dict):
        slide["image"] = {"source": "none", "material_ref": None, "prompt": None}
        return
    image.setdefault("source", "none")
    if image.get("source") not in ("none", "materials", "generate"):
        image["source"] = "none"
    placement = image.get("placement")
    if placement not in ("left", "right", "vertical", None):
        image["placement"] = "right"


def _table_payload_valid(slide: Dict[str, Any]) -> bool:
    table = slide.get("table")
    if not isinstance(table, dict):
        return False
    headers = _as_str_list(table.get("headers"), max_items=6)
    rows = _normalize_table_rows(table.get("rows"))
    return bool(headers) and bool(rows)


def _convert_invalid_table_to_cards(slide: Dict[str, Any]) -> Dict[str, Any]:
    texts: List[str] = []
    table = slide.get("table")
    if isinstance(table, dict):
        texts.extend(_as_str_list(table.get("headers"), max_items=6))
        for row in _normalize_table_rows(table.get("rows")):
            texts.append(" — ".join(cell for cell in row if cell))
    texts.extend(_as_str_list(slide.get("rows"), max_items=8))
    texts.extend(_as_str_list(slide.get("items") or slide.get("bullets"), max_items=8))
    if slide.get("subtitle"):
        texts.insert(0, _as_str(slide.get("subtitle")))
    if not texts:
        texts = [_as_str(slide.get("title"), "Содержание слайда")]
    slide["type"] = "cards"
    slide.pop("table", None)
    slide["cards"] = [{"title": f"Пункт {i + 1}", "text": text} for i, text in enumerate(texts[:6])]
    return slide


def _set_table_payload(slide: Dict[str, Any], headers: List[str], rows: List[List[str]]) -> None:
    headers = headers[:6] if headers else ["Показатель", "Значение"]
    rows = rows[:8]
    if not rows:
        rows = [["—"] * len(headers)]
    slide["table"] = {"headers": headers, "rows": rows}


def _normalize_table(slide: Dict[str, Any]) -> Dict[str, Any]:
    raw_table = slide.get("table")

    if isinstance(raw_table, str) and raw_table.strip():
        slide.pop("table", None)
        slide.setdefault("subtitle", raw_table.strip())
        return _convert_invalid_table_to_cards(slide)

    if isinstance(raw_table, list):
        slide.pop("table", None)
        if raw_table and all(isinstance(row, list) for row in raw_table):
            _set_table_payload(
                slide,
                [_as_str(cell) for cell in raw_table[0][:6]],
                [[_as_str(cell) for cell in row[:6]] for row in raw_table[1:9]],
            )
            return slide if _table_payload_valid(slide) else _convert_invalid_table_to_cards(slide)

    if isinstance(raw_table, dict):
        headers = _as_str_list(
            raw_table.get("headers") or raw_table.get("columns") or raw_table.get("header"),
            max_items=6,
        )
        rows = _normalize_table_rows(
            raw_table.get("rows") or raw_table.get("data") or raw_table.get("cells") or raw_table.get("body")
        )
        if headers or rows:
            _set_table_payload(slide, headers, rows)
            return slide if _table_payload_valid(slide) else _convert_invalid_table_to_cards(slide)
        slide.pop("table", None)

    headers = _as_str_list(slide.pop("headers", None), max_items=6)
    rows = _normalize_table_rows(slide.pop("rows", None))

    for key in ("data", "table_data", "table_content", "grid", "cells"):
        if key not in slide:
            continue
        value = slide.pop(key)
        if isinstance(value, list) and value:
            if all(isinstance(row, list) for row in value):
                if not headers and value:
                    headers = [_as_str(cell) for cell in value[0][:6]]
                    rows = [[_as_str(cell) for cell in row[:6]] for row in value[1:9]]
                elif not rows:
                    rows = [[_as_str(cell) for cell in row[:6]] for row in value[:8]]
            elif all(isinstance(row, dict) for row in value):
                rows = _normalize_table_rows(value)
        break

    if headers or rows:
        _set_table_payload(slide, headers, rows)
        return slide if _table_payload_valid(slide) else _convert_invalid_table_to_cards(slide)

    return _convert_invalid_table_to_cards(slide)


def _normalize_table_rows(rows: Any) -> List[List[str]]:
    if not rows:
        return []
    if isinstance(rows, list):
        if rows and all(isinstance(row, list) for row in rows):
            return [[_as_str(cell) for cell in row[:6]] for row in rows[:8]]
        if rows and all(isinstance(row, str) for row in rows):
            return [[text] for text in rows[:8]]
        if rows and all(isinstance(row, dict) for row in rows):
            parsed: List[List[str]] = []
            for row in rows[:8]:
                parsed.append([_as_str(v) for v in row.values()][:6])
            return parsed
    return []


def _normalize_comparison(slide: Dict[str, Any]) -> Dict[str, Any]:
    if isinstance(slide.get("left"), dict) and isinstance(slide.get("right"), dict):
        slide["left"] = _comparison_side(slide["left"], default_heading="Вариант A")
        slide["right"] = _comparison_side(slide["right"], default_heading="Вариант B")
        return slide

    columns = slide.pop("columns", None) or slide.pop("sides", None)
    if isinstance(columns, list) and len(columns) >= 2:
        slide["left"] = _comparison_side(columns[0], default_heading="До")
        slide["right"] = _comparison_side(columns[1], default_heading="После")
        return slide

    before = slide.pop("before", None)
    after = slide.pop("after", None)
    if before is not None or after is not None:
        slide["left"] = _comparison_side(before, default_heading="До")
        slide["right"] = _comparison_side(after, default_heading="После")
        return slide

    left_points = _as_str_list(slide.pop("left_points", None) or slide.pop("pros", None), max_items=5)
    right_points = _as_str_list(slide.pop("right_points", None) or slide.pop("cons", None), max_items=5)
    if left_points or right_points:
        slide["left"] = {"heading": "Вариант A", "points": left_points or ["—"]}
        slide["right"] = {"heading": "Вариант B", "points": right_points or ["—"]}
        return slide

    items = _as_str_list(slide.get("items") or slide.get("bullets"), max_items=8)
    if len(items) >= 2:
        mid = max(1, len(items) // 2)
        slide["left"] = {"heading": "Вариант A", "points": items[:mid]}
        slide["right"] = {"heading": "Вариант B", "points": items[mid:]}
        return slide

    slide["type"] = "cards"
    slide["cards"] = [
        {"title": slide.get("title") or "Сравнение", "text": slide.get("subtitle") or "Данные уточняются"}
    ]
    slide.pop("left", None)
    slide.pop("right", None)
    return slide


def _normalize_cards(slide: Dict[str, Any]) -> None:
    cards = slide.get("cards")
    if not isinstance(cards, list):
        items = _as_str_list(slide.get("items") or slide.get("bullets"), max_items=6)
        slide["cards"] = [{"title": f"Пункт {i + 1}", "text": t} for i, t in enumerate(items)]
        cards = slide["cards"]

    normalized: List[Dict[str, Any]] = []
    for index, card in enumerate(cards[:6]):
        if isinstance(card, str):
            normalized.append({"title": f"Пункт {index + 1}", "text": card})
            continue
        if not isinstance(card, dict):
            continue
        highlight = card.get("highlight")
        if isinstance(highlight, bool):
            highlight = "важно" if highlight else None
        elif highlight is not None:
            highlight = _as_str(highlight) or None
        normalized.append(
            {
                "title": _as_str(card.get("title") or card.get("heading") or f"Пункт {index + 1}"),
                "text": _as_str(card.get("text") or card.get("body") or card.get("description")),
                "highlight": highlight,
            }
        )
    while len(normalized) < 2:
        normalized.append({"title": f"Пункт {len(normalized) + 1}", "text": "—"})
    slide["cards"] = normalized[:6]


def _normalize_metrics(slide: Dict[str, Any]) -> None:
    metrics = slide.get("metrics")
    if not isinstance(metrics, list):
        metrics = []
    normalized: List[Dict[str, str]] = []
    for item in metrics[:6]:
        if isinstance(item, dict):
            normalized.append(
                {
                    "value": _as_str(item.get("value") or item.get("number") or "—", "—"),
                    "label": _as_str(item.get("label") or item.get("title") or item.get("name"), "Показатель"),
                    "note": _as_str(item.get("note")) or None,
                }
            )
        elif isinstance(item, str):
            parts = item.split(maxsplit=1)
            normalized.append(
                {
                    "value": parts[0] if parts else "—",
                    "label": parts[1] if len(parts) > 1 else item,
                }
            )
    if len(normalized) < 2:
        for text in _as_str_list(slide.get("items") or slide.get("bullets"), max_items=4):
            parts = text.split(maxsplit=1)
            normalized.append(
                {"value": parts[0], "label": parts[1] if len(parts) > 1 else text}
            )
    while len(normalized) < 2:
        normalized.append({"value": "—", "label": f"Показатель {len(normalized) + 1}"})
    slide["metrics"] = normalized[:6]


def _normalize_steps(slide: Dict[str, Any], *, key: str) -> None:
    steps = slide.get(key)
    if not isinstance(steps, list):
        steps = _as_str_list(slide.get("items") or slide.get("bullets"), max_items=7)
        if key == "steps" and slide.get("type") == "timeline":
            slide[key] = [{"label": text, "description": None} for text in steps]
        elif key == "steps":
            slide[key] = [{"title": text, "description": None} for text in steps]
        steps = slide.get(key)

    normalized: List[Dict[str, Any]] = []
    for index, step in enumerate((steps or [])[:7]):
        if isinstance(step, str):
            if slide.get("type") == "timeline":
                normalized.append({"label": step, "description": None})
            else:
                normalized.append({"title": step, "description": None})
            continue
        if not isinstance(step, dict):
            continue
        description = _as_str(step.get("description") or step.get("desc") or step.get("text")) or None
        if slide.get("type") == "timeline":
            normalized.append(
                {
                    "label": _as_str(step.get("label") or step.get("title") or f"Шаг {index + 1}"),
                    "description": description,
                }
            )
        else:
            normalized.append(
                {
                    "title": _as_str(step.get("title") or step.get("label") or f"Шаг {index + 1}"),
                    "description": description,
                }
            )
    while len(normalized) < 3:
        if slide.get("type") == "timeline":
            normalized.append({"label": f"Шаг {len(normalized) + 1}", "description": None})
        else:
            normalized.append({"title": f"Шаг {len(normalized) + 1}", "description": None})
    slide[key] = normalized[:7]


def _normalize_list_field(slide: Dict[str, Any], field: str, *, min_items: int = 2) -> None:
    items = _as_str_list(slide.get(field) or slide.get("items") or slide.get("bullets"), max_items=8)
    while len(items) < min_items:
        items.append(f"Пункт {len(items) + 1}")
    slide[field] = items[:8]
    slide.pop("items", None)
    slide.pop("bullets", None)


def normalize_slide_payload(slide: Dict[str, Any]) -> Dict[str, Any]:
    """Приводит сырой JSON от LLM к полям, ожидаемым Pydantic-моделями."""
    item = dict(slide)
    item["type"] = _as_str(item.get("type") or "cards", "cards")
    item["title"] = _as_str(item.get("title") or "Слайд", "Слайд")
    _ensure_image(item)

    slide_type = item["type"]

    if slide_type == "comparison":
        item = _normalize_comparison(item)
        slide_type = item["type"]

    if slide_type == "table":
        item = _normalize_table(item)
        slide_type = item["type"]

    if slide_type == "cards":
        _normalize_cards(item)
    elif slide_type == "kpi":
        _normalize_metrics(item)
    elif slide_type == "timeline":
        _normalize_steps(item, key="steps")
    elif slide_type == "process":
        _normalize_steps(item, key="steps")
    elif slide_type == "agenda":
        _normalize_list_field(item, "items", min_items=3)
    elif slide_type == "problem":
        _normalize_list_field(item, "pain_points", min_items=2)
    elif slide_type == "goals":
        _normalize_list_field(item, "goals", min_items=2)
    elif slide_type == "conclusion":
        _normalize_list_field(item, "takeaways", min_items=2)
    elif slide_type == "results":
        results = item.get("results")
        if not isinstance(results, list) or len(results) < 2:
            item["results"] = [
                {"label": f"Итог {i + 1}", "value": text}
                for i, text in enumerate(_as_str_list(item.get("items"), max_items=6))
            ]
        parsed_results: List[Dict[str, Any]] = []
        for entry in item.get("results") or []:
            if isinstance(entry, dict):
                parsed_results.append(
                    {
                        "label": _as_str(entry.get("label"), "Итог"),
                        "value": _as_str(entry.get("value"), "—"),
                        "trend": entry.get("trend")
                        if entry.get("trend") in ("up", "down", "neutral")
                        else None,
                    }
                )
        while len(parsed_results) < 2:
            parsed_results.append({"label": f"Итог {len(parsed_results) + 1}", "value": "—"})
        item["results"] = parsed_results[:6]
    elif slide_type == "diagram":
        points = _as_str_list(item.get("key_points") or item.get("items"), max_items=4)
        item["key_points"] = points or ["Ключевая мысль"]

    if item.get("type") == "table" and not _table_payload_valid(item):
        item = _normalize_table(item)
    if item.get("type") == "table" and not _table_payload_valid(item):
        item = _convert_invalid_table_to_cards(item)
        _normalize_cards(item)

    return item
