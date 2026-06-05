from __future__ import annotations

from typing import List

from app.ai.registry import chat_with_agent_resilient
from app.ai.types import ChatMessage
from app.config import get_settings

settings = get_settings()


async def chat_for_blueprint(agent_id: str, messages: List[ChatMessage]) -> str:
    """Blueprint через выбранного агента (по умолчанию mimo) с fallback без автоматического Polza."""
    effective = agent_id or settings.presentation_default_agent
    return await chat_with_agent_resilient(effective, messages)
