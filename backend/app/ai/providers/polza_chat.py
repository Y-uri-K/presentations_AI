from __future__ import annotations

import logging
import time
from typing import List

import httpx
from fastapi import HTTPException, status

from app.ai.http_errors import raise_provider_http_error
from app.ai.safety import raise_if_safety_rejection
from app.ai.types import ChatMessage
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


async def polza_chat_completions(
    messages: List[ChatMessage],
    *,
    model: str | None = None,
    timeout_seconds: float | None = None,
) -> str:
    """
    OpenAI-совместимый chat/completions Polza.ai.
    Документация: https://polza.ai/docs/api-reference/chat/completions
    """
    if not settings.polza_api_key.strip():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Polza AI не настроен. Укажите POLZA_API_KEY в .env",
        )

    model_id = model or settings.polza_chat_model
    timeout = timeout_seconds if timeout_seconds is not None else settings.polza_chat_timeout_seconds
    base_url = settings.polza_base_url.rstrip("/")
    headers = {
        "Authorization": f"Bearer {settings.polza_api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model_id,
        "messages": [{"role": m.role, "content": m.content} for m in messages],
        "stream": False,
        "temperature": 0.3,
    }

    started = time.perf_counter()
    logger.info("Polza chat: модель=%s, сообщений=%s", model_id, len(messages))
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                f"{base_url}/chat/completions",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPStatusError as exc:
        raise_provider_http_error("Polza AI", exc)
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Не удалось подключиться к Polza AI: {exc}",
        ) from exc

    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Polza AI вернула неожиданный формат ответа chat/completions",
        ) from exc

    text = str(content).strip()
    if not text:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Polza AI вернула пустой ответ",
        )
    raise_if_safety_rejection(text, provider_name="Polza AI")
    logger.info(
        "Polza chat ответ: модель=%s, %s символов за %.1f с",
        model_id,
        len(text),
        time.perf_counter() - started,
    )
    return text
