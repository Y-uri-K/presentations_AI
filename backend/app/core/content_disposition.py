from __future__ import annotations

import re
from urllib.parse import quote


def attachment_content_disposition(filename: str) -> str:
    """RFC 5987: ASCII fallback + UTF-8 filename for non-Latin names."""
    normalized = filename.strip() or "presentation.pptx"
    if not normalized.lower().endswith(".pptx"):
        normalized = f"{normalized}.pptx"

    ascii_fallback = re.sub(r"[^\w.\- ]", "_", normalized, flags=re.ASCII).strip()
    ascii_fallback = re.sub(r"\s+", "_", ascii_fallback) or "presentation.pptx"

    encoded = quote(normalized, safe="")
    return f"attachment; filename=\"{ascii_fallback}\"; filename*=UTF-8''{encoded}"
