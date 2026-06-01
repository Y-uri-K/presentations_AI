from __future__ import annotations

import re

from app.services.template_driven.constants import PLACEHOLDER_BANNED_RE


def word_count(text: str) -> int:
    return len(re.findall(r"\w+", text, flags=re.UNICODE))


def is_placeholder_text(text: str) -> bool:
    stripped = (text or "").strip()
    if not stripped:
        return True
    return bool(PLACEHOLDER_BANNED_RE.search(stripped))
