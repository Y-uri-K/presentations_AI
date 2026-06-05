from __future__ import annotations

from typing import List

from fastapi import HTTPException, status

from app.ai.providers.polza_chat import polza_chat_completions
from app.ai.types import AgentInfo, ChatMessage
from app.config import get_settings

settings = get_settings()


class PolzaProvider:
    id = "polza"

    async def get_info(self) -> AgentInfo:
        has_key = bool(settings.polza_api_key.strip())
        return AgentInfo(
            id=self.id,
            name="Polza (Gemini 3.5 Flash)",
            description="Чат-модель Polza.ai — используйте осознанно (платный API)",
            model=settings.polza_chat_model,
            provider="polza",
            available=has_key,
            unavailable_reason=None if has_key else "Укажите POLZA_API_KEY в .env",
        )

    async def chat(self, messages: List[ChatMessage]) -> str:
        return await polza_chat_completions(messages)
