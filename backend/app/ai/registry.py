from __future__ import annotations

import logging
import time
from typing import List

from fastapi import HTTPException, status

from app.ai.providers.mimo import MimoProvider
from app.ai.providers.ollama import OllamaProvider
from app.ai.providers.polza_agent import PolzaProvider
from app.ai.types import AgentInfo, ChatMessage
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_PROVIDERS = {
    "ollama": OllamaProvider(),
    "polza": PolzaProvider(),
    "mimo": MimoProvider(),
}

_RETRYABLE_STATUS = frozenset(
    {
        status.HTTP_503_SERVICE_UNAVAILABLE,
        status.HTTP_502_BAD_GATEWAY,
        status.HTTP_429_TOO_MANY_REQUESTS,
    }
)

_LEGACY_AGENT_ALIASES = {
    "gemini": "mimo",
}


def resolve_agent_id(agent_id: str) -> str:
    """Нормализация id (устаревший gemini → mimo)."""
    return _LEGACY_AGENT_ALIASES.get(agent_id, agent_id)


def _parse_agent_list(raw: str) -> tuple[str, ...]:
    excluded = frozenset({"polza", "gemini"})
    return tuple(
        resolve_agent_id(item.strip())
        for item in raw.split(",")
        if item.strip()
        and item.strip() not in excluded
        and resolve_agent_id(item.strip()) in _PROVIDERS
    )


def fallback_agent_order() -> tuple[str, ...]:
    """Обычный fallback без Polza: mimo → ollama."""
    order = _parse_agent_list(settings.presentation_llm_fallback_agents)
    if not order:
        order = ("mimo", "ollama")
    return order


def get_provider(agent_id: str):
    resolved = resolve_agent_id(agent_id)
    provider = _PROVIDERS.get(resolved)
    if provider is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Агент «{agent_id}» не найден",
        )
    return provider


async def list_agents() -> List[AgentInfo]:
    agents: List[AgentInfo] = []
    for _agent_id, provider in _PROVIDERS.items():
        agents.append(await provider.get_info())
    return agents


async def chat_with_agent(agent_id: str, messages: List[ChatMessage]) -> str:
    resolved = resolve_agent_id(agent_id)
    provider = get_provider(agent_id)
    info = await provider.get_info()
    if not info.available:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=info.unavailable_reason or "Агент недоступен",
        )
    if resolved != agent_id:
        logger.info("Агент %s → %s (%s)", agent_id, resolved, info.model)
    return await provider.chat(messages)


def _agent_attempt_order(preferred_agent_id: str) -> List[str]:
    preferred = resolve_agent_id(preferred_agent_id)
    order: List[str] = []
    if preferred in _PROVIDERS:
        order.append(preferred)
    for agent_id in fallback_agent_order():
        if agent_id not in order:
            order.append(agent_id)
    critical = resolve_agent_id(settings.presentation_critical_fallback_agent.strip())
    if critical == "polza" and critical not in order and settings.polza_api_key.strip():
        order.append(critical)
    return order


async def chat_with_agent_resilient(agent_id: str, messages: List[ChatMessage]) -> str:
    """
    Основной агент (по умолчанию mimo), при 502/503/429 — ollama и др. из fallback.
    Polza — только если пользователь выбрал polza, либо последний критический fallback.
    """
    errors: List[str] = []
    attempt_order = _agent_attempt_order(agent_id)
    for candidate_id in attempt_order:
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
