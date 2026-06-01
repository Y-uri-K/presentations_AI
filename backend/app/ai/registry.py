from __future__ import annotations

import logging
import time
from typing import List

from fastapi import HTTPException, status

from app.ai.providers.gemini import GeminiProvider
from app.ai.providers.mimo import MimoProvider
from app.ai.providers.ollama import OllamaProvider
from app.ai.providers.polza_agent import PolzaProvider
from app.config import get_settings
from app.ai.types import AgentInfo, ChatMessage
logger = logging.getLogger(__name__)
settings = get_settings()

_PROVIDERS = {
    "ollama": OllamaProvider(),
    "gemini": GeminiProvider(),
    "polza": PolzaProvider(),
    "mimo": MimoProvider(),
}

_FALLBACK_AGENT_ORDER = ("polza", "gemini", "mimo", "ollama")
_RETRYABLE_STATUS = frozenset(
    {
        status.HTTP_503_SERVICE_UNAVAILABLE,
        status.HTTP_502_BAD_GATEWAY,
        status.HTTP_429_TOO_MANY_REQUESTS,
    }
)


def resolve_agent_id(agent_id: str) -> str:
    """gemini → polza, если настроен POLZA_API_KEY (Gemini 3.5 Flash)."""
    if agent_id == "gemini" and settings.polza_api_key.strip():
        return "polza"
    return agent_id


def get_provider(agent_id: str):
    provider = _PROVIDERS.get(resolve_agent_id(agent_id))
    if provider is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Агент «{agent_id}» не найден",
        )
    return provider


async def list_agents() -> List[AgentInfo]:
    agents: List[AgentInfo] = []
    use_polza = bool(settings.polza_api_key.strip())
    for agent_id, provider in _PROVIDERS.items():
        if agent_id == "polza" and use_polza:
            continue
        agents.append(await provider.get_info())
    return agents


async def chat_with_agent(agent_id: str, messages: List[ChatMessage]) -> str:
    effective_id = resolve_agent_id(agent_id)
    provider = get_provider(agent_id)
    info = await provider.get_info()
    if not info.available:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=info.unavailable_reason or "Агент недоступен",
        )
    if effective_id != agent_id:
        logger.info("Агент %s → %s (%s)", agent_id, effective_id, info.model)
    return await provider.chat(messages)


def _agent_attempt_order(preferred_agent_id: str) -> List[str]:
    order: List[str] = []
    for agent_id in (resolve_agent_id(preferred_agent_id), *_FALLBACK_AGENT_ORDER):
        resolved = resolve_agent_id(agent_id)
        if resolved in _PROVIDERS and resolved not in order:
            order.append(resolved)
    return order


async def chat_with_agent_resilient(agent_id: str, messages: List[ChatMessage]) -> str:
    """Пробует основной агент, при 502/503/429 — следующий доступный."""
    errors: List[str] = []
    for candidate_id in _agent_attempt_order(agent_id):
        started = time.perf_counter()
        logger.info("Запрос к ИИ: агент=%s", candidate_id)
        try:
            content = await chat_with_agent(candidate_id, messages)
            logger.info(
                "Ответ ИИ: агент=%s, %s символов, %.1f с",
                candidate_id,
                len(content),
                time.perf_counter() - started,
            )
            return content
        except HTTPException as exc:
            logger.warning(
                "ИИ агент=%s ошибка за %.1f с: %s",
                candidate_id,
                time.perf_counter() - started,
                exc.detail,
            )
            if exc.status_code not in _RETRYABLE_STATUS:
                raise
            message = f"{candidate_id}: {exc.detail}"
            errors.append(message)
            logger.warning("Агент недоступен, пробуем следующий: %s", message)
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="ИИ недоступен. " + (" | ".join(errors) if errors else "Нет настроенных агентов."),
    )
