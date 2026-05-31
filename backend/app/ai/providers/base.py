from __future__ import annotations

from typing import List, Protocol

from app.ai.types import AgentInfo, ChatMessage


class ChatProvider(Protocol):
    id: str

    async def get_info(self) -> AgentInfo: ...

    async def chat(self, messages: List[ChatMessage]) -> str: ...
