from __future__ import annotations

from app.config import get_settings

DEFAULT_LAYOUTS = """
## ДОСТУПНЫЕ МАКЕТЫ (ровно один тег на слайд)

1. BULLETS — ключевые пункты
```xml
<BULLETS>
  <DIV><H3>Заголовок пункта</H3><P>Описание</P></DIV>
</BULLETS>
```

2. STATS — KPI / метрики
```xml
<STATS>
  <DIV><H3>15%</H3><P>Рост выручки</P></DIV>
</STATS>
```

3. TIMELINE — хронология
```xml
<TIMELINE>
  <DIV><H3>2024</H3><P>Событие</P></DIV>
</TIMELINE>
```

4. CYCLE / ARROWS / ARROW-VERTICAL / STAIRCASE / PYRAMID — процесс, этапы
```xml
<ARROWS>
  <DIV><H3>Шаг 1</H3><P>Описание</P></DIV>
</ARROWS>
```

5. BOXES / ICONS — плитки / иконки
```xml
<BOXES>
  <DIV><H3>Скорость</H3><P>Краткое описание</P></DIV>
</BOXES>
```

6. COLUMNS / COMPARE / BEFORE-AFTER / PROS-CONS — сравнение
```xml
<COMPARE>
  <DIV><H3>Вариант A</H3><P>Пункт</P></DIV>
  <DIV><H3>Вариант B</H3><P>Пункт</P></DIV>
</COMPARE>
```

7. TABLE — таблица
```xml
<TABLE>
  <TR><TH>Колонка 1</TH><TH>Колонка 2</TH></TR>
  <TR><TD>Данные</TD><TD>Данные</TD></TR>
</TABLE>
```

8. CHART — диаграмма (данные в DIV)
```xml
<CHART chartType="bar">
  <DIV><H3>Q1</H3><P>24</P></DIV>
</CHART>
```
"""


def outline_system_prompt() -> str:
    settings = get_settings()
    n = settings.presentation_max_slides
    return f"""Ты эксперт по структуре презентаций. Создай план на русском языке.

Дата: {{current_date}}
Уровень текста: {{text_content}}
Тон: {{tone}}
Аудитория: {{audience}}
Сценарий: {{scenario}}

Процесс:
1. Проанализируй тему
2. Сформируй ровно {n} тем (слайдов)
3. На каждую тему — заголовок и 2–3 пункта списка через "- "; каждый пункт — минимум 2 полных предложения

Требования:
- Сначала одна строка: <TITLE>название презентации</TITLE> (это НЕ слайд, в план не входит)
- Затем только темы слайдов: для каждой темы "# Заголовок темы" и буллеты "- пункт"
- Не дублируй текст из <TITLE> в заголовках # и не добавляй для названия отдельный слайд
- Ровно {n} тем (ровно {n} заголовков с #, без учёта <TITLE>)
- Без жирного/курсива
- Не копируй запрос дословно — разверни содержательно
"""


def slides_xml_system_prompt() -> str:
    settings = get_settings()
    max_images = settings.presentation_max_generated_images
    return f"""Ты — дизайнер презентаций. Создай презентацию в XML (как Gamma / ALLWEONE presentation-ai).

Контекст:
- Название: {{title}}
- Запрос: {{prompt}}
- Дата: {{current_date}}
- Язык: {{language}}
- Тон: {{tone}}
- Слайдов: {{total_slides}} (ровно столько SECTION)
- Уровень текста: {{text_content}}
- Аудитория: {{audience}}

План (один SECTION на блок):
```md
{{outline_formatted}}
```

{{search_results}}

ФОРМАТ ОТВЕТА — только XML:
```xml
<PRESENTATION>
  <SECTION layout="left|right|vertical">
    <!-- один макет: BULLETS, STATS, TIMELINE, ... -->
    <IMG query="краткий запрос на картинку на английском для стока" />
  </SECTION>
</PRESENTATION>
```

Атрибут SECTION layout: чередуй left, right, vertical.

{DEFAULT_LAYOUTS}

КАРТИНКИ:
- Тег <IMG query="..." /> — короткий запрос на английском (1–4 слова) для поиска/генерации
- Добавляй <IMG query="..." /> на важных слайдах (до {max_images} с IMG) — картинки будут сгенерированы и вставлены в PPTX

ПРАВИЛА:
1. Ровно {{total_slides}} тегов SECTION — не больше и не меньше
2. Не повторяй один и тот же макет на соседних слайдах
3. Разверни план — не копируй буллеты дословно
4. Первый слайд — титульный (BULLETS с названием и подзаголовком)
5. Последний — выводы (BULLETS или STATS) или благодарность
6. Используй только перечисленные теги макетов
"""
