from __future__ import annotations

import logging
import time
from typing import List

from fastapi import HTTPException, status

from app.ai.providers.polza_chat import polza_chat_completions
from app.ai.registry import chat_with_agent_resilient
from app.ai.types import ChatMessage
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_RETRYABLE = frozenset(
    {
        status.HTTP_503_SERVICE_UNAVAILABLE,
        status.HTTP_502_BAD_GATEWAY,
        status.HTTP_429_TOO_MANY_REQUESTS,
    }
)


async def chat_for_blueprint(agent_id: str, messages: List[ChatMessage]) -> str:
    """Blueprint через Polza (быстро), при сбое — выбранный агент с fallback."""
    if settings.presentation_blueprint_use_polza and settings.polza_api_key.strip():
        started = time.perf_counter()
        try:
            content = await polza_chat_completions(messages)
            logger.info(
                "Blueprint Polza (%s): %s символов за %.1f с",
                settings.polza_chat_model,
                len(content),
                time.perf_counter() - started,
            )
            return content
        except HTTPException as exc:
            logger.warning(
                "Blueprint Polza недоступен за %.1f с (%s), fallback на агентов",
                time.perf_counter() - started,
                exc.detail,
            )
            if exc.status_code not in _RETRYABLE:
                raise
        except Exception as exc:
            logger.warning("Blueprint Polza: %s, fallback на агентов", exc)

    return await chat_with_agent_resilient(agent_id, messages)
