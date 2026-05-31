from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field

AgentId = Literal["ollama", "gemini", "mimo"]


class AgentInfoResponse(BaseModel):
    id: str
    name: str
    description: str
    model: str
    provider: str
    available: bool
    unavailable_reason: Optional[str] = None


class ChatMessageSchema(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=32000)


class AgentChatRequest(BaseModel):
    agent_id: AgentId
    message: str = Field(min_length=1, max_length=32000)
    history: List[ChatMessageSchema] = Field(default_factory=list, max_length=50)


class AgentChatResponse(BaseModel):
    agent_id: AgentId
    model: str
    reply: str
