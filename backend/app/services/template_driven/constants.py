from __future__ import annotations

import re

PLACEHOLDER_BANNED_RE = re.compile(
    r"^\s*$|^\s*-\s*$|пункт\s*\d+|введите\s+текст|заголовок\s*слайда|"
    r"заг\b|подзаголовок|текст\s+презентации|раздел\s*\d*|"
    r"click\s+to\s+edit|lorem\s+ipsum|здесь\s+будет",
    re.IGNORECASE,
)

MIN_WORDS_BY_ROLE = {
    "title": 5,
    "subtitle": 5,
    "section_title": 5,
    "card_title": 3,
    "card_body": 20,
    "body": 30,
    "bullet": 8,
    "column_heading": 3,
    "column_point": 8,
    "metric_value": 1,
    "metric_label": 3,
    "table_cell": 2,
    "timeline_label": 3,
    "timeline_body": 10,
    "caption": 5,
    "default": 10,
}

SLIDE_SCORE_THRESHOLD = 0.8
MAX_SAME_LAYOUT_IN_ROW = 2
