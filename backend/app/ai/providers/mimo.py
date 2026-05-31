from __future__ import annotations

from typing import List

import httpx
from fastapi import HTTPException, status

from app.ai.http_errors import raise_provider_http_error
from app.ai.types import AgentInfo, ChatMessage
from app.config import get_settings

settings = get_settings()


class MimoProvider:
    id = "mimo"

    async def get_info(self) -> AgentInfo:
        has_key = bool(settings.mimi_api_key.strip())
        return AgentInfo(
            id=self.id,
            name="Xiaomi MiMo",
            description="Облачная модель Xiaomi MiMo (OpenAI-совместимый API)",
            model=settings.mimi_model,
            provider="mimo",
            available=has_key,
            unavailable_reason=None if has_key else "Укажите MIMI_API_KEY в .env",
        )

    async def chat(self, messages: List[ChatMessage]) -> str:
        if not settings.mimi_api_key.strip():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="MiMo не настроен. Укажите MIMI_API_KEY в .env",
            )

        payload = {
            "model": settings.mimi_model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": False,
        }
        headers = {
            "Authorization": f"Bearer {settings.mimi_api_key}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=settings.mimi_timeout_seconds) as client:
                response = await client.post(
                    f"{settings.mimi_base_url.rstrip('/')}/chat/completions",
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPStatusError as exc:
            raise_provider_http_error("Xiaomi MiMo", exc)
        except httpx.RequestError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Не удалось подключиться к MiMo: {exc}",
            ) from exc

        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="MiMo вернула неожиданный формат ответа",
            ) from exc

        if not str(content).strip():
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="MiMo вернула пустой ответ",
            )
        return str(content).strip()
