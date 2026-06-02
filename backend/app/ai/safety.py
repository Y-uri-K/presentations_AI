from __future__ import annotations

from fastapi import HTTPException, status

_REJECTION_MARKERS = (
    "the request was rejected because it was considered high risk",
    "request was rejected",
    "considered high risk",
    "safety policy",
    "safety reasons",
    "blocked due to safety",
    "blocked by safety",
)


def is_safety_rejection(text: str) -> bool:
    normalized = " ".join((text or "").strip().lower().split())
    return any(marker in normalized for marker in _REJECTION_MARKERS)


def raise_if_safety_rejection(text: str, *, provider_name: str = "ИИ") -> None:
    if not is_safety_rejection(text):
        return
    raise HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail=(
            f"{provider_name} отклонил запрос как потенциально рискованный. "
            "Переформулируйте тему нейтральнее или выберите другого ИИ-агента."
        ),
    )
