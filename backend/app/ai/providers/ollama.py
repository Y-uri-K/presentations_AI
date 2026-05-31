from __future__ import annotations

from typing import List

import httpx
from fastapi import HTTPException, status

from app.ai.http_errors import raise_provider_http_error
from app.ai.types import AgentInfo, ChatMessage
from app.config import get_settings

settings = get_settings()


class OllamaProvider:
    id = "ollama"

    async def get_info(self) -> AgentInfo:
        available = await self._is_reachable()
        return AgentInfo(
            id=self.id,
            name="Ollama (локально)",
            description="Локальная модель через Ollama на вашем компьютере",
            model=settings.ollama_model,
            provider="ollama",
            available=available,
            unavailable_reason=None if available else "Ollama недоступна. Запустите ollama serve на хосте.",
        )

    async def chat(self, messages: List[ChatMessage]) -> str:
        if not await self._is_reachable():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Ollama недоступна. Запустите ollama serve и проверьте OLLAMA_BASE_URL.",
            )

        payload = {
            "model": settings.ollama_model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": False,
        }

        try:
            async with httpx.AsyncClient(timeout=settings.ollama_timeout_seconds) as client:
                response = await client.post(
                    f"{settings.ollama_base_url.rstrip('/')}/api/chat",
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPStatusError as exc:
            raise_provider_http_error("Ollama", exc)
        except httpx.RequestError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Не удалось подключиться к Ollama: {exc}",
            ) from exc

        content = data.get("message", {}).get("content")
        if not content:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Ollama вернула пустой ответ",
            )
        return str(content).strip()

    async def _is_reachable(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{settings.ollama_base_url.rstrip('/')}/api/tags")
                return response.status_code == 200
        except httpx.RequestError:
            return False
