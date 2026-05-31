from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends

from app.ai.registry import chat_with_agent, get_provider, list_agents
from app.ai.types import ChatMessage
from app.core.deps import get_current_user
from app.models import User
from app.schemas.agents import AgentChatRequest, AgentChatResponse, AgentInfoResponse

router = APIRouter(prefix="/api/agents", tags=["agents"])


@router.get("", response_model=List[AgentInfoResponse])
async def get_agents(_current_user: User = Depends(get_current_user)):
    agents = await list_agents()
    return [AgentInfoResponse(**agent.__dict__) for agent in agents]


@router.post("/chat", response_model=AgentChatResponse)
async def agent_chat(
    payload: AgentChatRequest,
    _current_user: User = Depends(get_current_user),
):
    messages = [
        ChatMessage(role=msg.role, content=msg.content) for msg in payload.history
    ]
    messages.append(ChatMessage(role="user", content=payload.message))

    reply = await chat_with_agent(payload.agent_id, messages)
    provider = get_provider(payload.agent_id)
    info = await provider.get_info()

    return AgentChatResponse(
        agent_id=payload.agent_id,
        model=info.model,
        reply=reply,
    )
