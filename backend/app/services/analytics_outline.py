from __future__ import annotations

import re
from typing import List, Optional

from app.schemas.slides import SlideImageSpec
from app.schemas.template_blueprint import (
    BlueprintMetric,
    BlueprintSlide,
    BlueprintTable,
)

_METRIC_VALUE_RE = re.compile(
    r"(\d[\d\s,.]*)\s*(%|₽|\$|€|pp|п\.п\.|руб\.?|тыс\.?|млн\.?|млрд\.?)?",
    re.IGNORECASE,
)
_LABEL_VALUE_RE = re.compile(
    r"^(.{2,60}?)\s*[:：\-–—]\s*(\d[\d\s,.]*\s*%?.*)$",
)
_ANALYTICS_TOPIC_RE = re.compile(
    r"анализ|аналитик|статистик|данн|показател|метрик|kpi|динамик|"
    r"отчёт|отчет|report|dashboard|график|chart|сводк|итог.*\d",
    re.IGNORECASE,
)
_TABLE_SEP_RE = re.compile(r"\||\t|;\s*(?=\S)")


def _chunk_text(chunk: str, bullets: List[str]) -> str:
    return f"{chunk}\n" + "\n".join(bullets)


def count_numeric_signals(text: str) -> int:
    return len(_METRIC_VALUE_RE.findall(text))


def detect_analytics_kind(chunk: str, bullets: List[str]) -> Optional[str]:
    """kpi | table | results — если в разделе есть аналитические данные."""
    text = _chunk_text(chunk, bullets)
    lowered = text.lower()

    if any(_TABLE_SEP_RE.search(line) for line in bullets):
        return "table"
    for line in bullets:
        parts = re.split(r"\s{2,}", line.strip())
        if len(parts) >= 3 and count_numeric_signals(line) >= 1:
            return "table"

    numeric_hits = count_numeric_signals(text)
    if numeric_hits >= 3:
        return "kpi"
    if numeric_hits >= 2 and _ANALYTICS_TOPIC_RE.search(text):
        return "kpi"
    if numeric_hits >= 1 and any(
        w in lowered for w in ("рост", "снижен", "прирост", "доля", "выручк", "конверси", "roi", "cac")
    ):
        return "kpi"
    if _ANALYTICS_TOPIC_RE.search(text) and len(bullets) >= 2:
        return "results"
    return None


def extract_metrics_from_bullets(bullets: List[str]) -> List[BlueprintMetric]:
    metrics: List[BlueprintMetric] = []
    for line in bullets:
        line = line.strip()
        if not line:
            continue
        labeled = _LABEL_VALUE_RE.match(line)
        if labeled:
            metrics.append(
                BlueprintMetric(
                    label=labeled.group(1).strip()[:48],
                    value=labeled.group(2).strip()[:24],
                )
            )
            continue
        numbers = _METRIC_VALUE_RE.findall(line)
        if numbers:
            value = numbers[0][0].strip() + (numbers[0][1] or "")
            label = _METRIC_VALUE_RE.sub("", line, count=1).strip(" -—:") or line[:48]
            metrics.append(BlueprintMetric(value=value[:24], label=label[:48]))
    while len(metrics) < 2 and bullets:
        metrics.append(
            BlueprintMetric(
                value="—",
                label=bullets[min(len(metrics), len(bullets) - 1)][:48],
            )
        )
    return metrics[:6]


def extract_table_from_bullets(bullets: List[str]) -> Optional[BlueprintTable]:
    rows: List[List[str]] = []
    for line in bullets:
        line = line.strip()
        if not line:
            continue
        if "|" in line:
            cells = [c.strip() for c in line.split("|") if c.strip()]
        elif "\t" in line:
            cells = [c.strip() for c in line.split("\t") if c.strip()]
        elif ";" in line:
            cells = [c.strip() for c in re.split(r";\s*", line) if c.strip()]
        else:
            cells = [c.strip() for c in re.split(r"\s{2,}", line) if c.strip()]
        if len(cells) >= 2:
            rows.append(cells[:6])
    if len(rows) >= 2:
        return BlueprintTable(headers=rows[0], rows=rows[1:8])
    if len(rows) == 1 and len(rows[0]) >= 2:
        return BlueprintTable(
            headers=["Показатель", "Значение"],
            rows=[[cell, ""] for cell in rows[0][:6]],
        )
    return None


def build_analytics_blueprint_slide(
    *,
    kind: str,
    topic_title: str,
    bullets: List[str],
    body: str,
) -> BlueprintSlide:
    if kind == "table":
        table = extract_table_from_bullets(bullets)
        if table:
            return BlueprintSlide(
                slide_type="table",
                template_key="",
                topic=topic_title,
                title=topic_title,
                subtitle=body[:300],
                bullets=bullets,
                table=table,
                image=SlideImageSpec(source="none"),
            )
    metrics = extract_metrics_from_bullets(bullets)
    if kind in ("kpi", "table") or metrics:
        return BlueprintSlide(
            slide_type="kpi",
            template_key="",
            topic=topic_title,
            title=topic_title,
            subtitle=body[:300],
            bullets=bullets,
            metrics=metrics,
            image=SlideImageSpec(source="none"),
        )
    return BlueprintSlide(
        slide_type="cards",
        template_key="",
        topic=topic_title,
        title=topic_title,
        subtitle=body[:300],
        bullets=bullets or [body],
        image=SlideImageSpec(source="none"),
    )
