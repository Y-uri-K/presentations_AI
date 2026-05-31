from __future__ import annotations

from typing import Dict, List

from fastapi import HTTPException, status

from app.ai.providers.gemini import GeminiProvider
from app.ai.providers.mimo import MimoProvider
from app.ai.providers.ollama import OllamaProvider
from app.ai.types import AgentInfo, ChatMessage

_PROVIDERS = {
    "ollama": OllamaProvider(),
    "gemini": GeminiProvider(),
    "mimo": MimoProvider(),
}


def get_provider(agent_id: str):
    provider = _PROVIDERS.get(agent_id)
    if provider is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Агент «{agent_id}» не найден",
        )
    return provider


async def list_agents() -> List[AgentInfo]:
    agents: List[AgentInfo] = []
    for provider in _PROVIDERS.values():
        agents.append(await provider.get_info())
    return agents


async def chat_with_agent(agent_id: str, messages: List[ChatMessage]) -> str:
    provider = get_provider(agent_id)
    info = await provider.get_info()
    if not info.available:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=info.unavailable_reason or "Агент недоступен",
        )
    return await provider.chat(messages)
