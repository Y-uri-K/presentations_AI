from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional

ChatRole = Literal["user", "assistant"]


@dataclass
class ChatMessage:
    role: ChatRole
    content: str


@dataclass
class AgentInfo:
    id: str
    name: str
    description: str
    model: str
    provider: str
    available: bool
    unavailable_reason: Optional[str] = None
