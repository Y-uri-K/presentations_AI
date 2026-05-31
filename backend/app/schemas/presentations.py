from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field

AgentId = Literal["ollama", "gemini", "mimo"]


class PresentationCreateResponse(BaseModel):
    outline: str
    agent_id: AgentId
    template_id: Optional[int] = None
    template_name: Optional[str] = None
    source_files: List[str] = Field(default_factory=list)
