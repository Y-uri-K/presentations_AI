from __future__ import annotations

from typing import List

import httpx
from fastapi import HTTPException, status

from app.ai.http_errors import raise_provider_http_error
from app.ai.providers.polza_chat import polza_chat_completions
from app.ai.types import AgentInfo, ChatMessage
from app.config import get_settings

settings = get_settings()


def _use_polza_for_gemini() -> bool:
    return bool(settings.polza_api_key.strip())


class GeminiProvider:
    id = "gemini"

    async def get_info(self) -> AgentInfo:
        if _use_polza_for_gemini():
            return AgentInfo(
                id=self.id,
                name="Gemini 3.5 Flash",
                description="Через Polza.ai (без прямой квоты Google API)",
                model=settings.polza_chat_model,
                provider="polza",
                available=True,
            )
        has_key = bool(settings.gemini_api_key.strip())
        return AgentInfo(
            id=self.id,
            name="Google Gemini",
            description="Прямой API Google Gemini",
            model=settings.gemini_model,
            provider="gemini",
            available=has_key,
            unavailable_reason=None if has_key else "Укажите POLZA_API_KEY или GEMINI_API_KEY в .env",
        )

    async def chat(self, messages: List[ChatMessage]) -> str:
        if _use_polza_for_gemini():
            return await polza_chat_completions(messages)

        if not settings.gemini_api_key.strip():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Gemini не настроен. Укажите POLZA_API_KEY или GEMINI_API_KEY в .env",
            )

        contents = []
        for message in messages:
            role = "user" if message.role == "user" else "model"
            contents.append({"role": role, "parts": [{"text": message.content}]})

        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{settings.gemini_model}:generateContent"
        )
        payload = {"contents": contents}

        try:
            async with httpx.AsyncClient(timeout=settings.gemini_timeout_seconds) as client:
                response = await client.post(
                    url,
                    params={"key": settings.gemini_api_key},
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPStatusError as exc:
            raise_provider_http_error("Google Gemini", exc)
        except httpx.RequestError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Не удалось подключиться к Gemini: {exc}",
            ) from exc

        try:
            parts = data["candidates"][0]["content"]["parts"]
            text = "".join(part.get("text", "") for part in parts)
        except (KeyError, IndexError, TypeError) as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Gemini вернула неожиданный формат ответа",
            ) from exc

        if not text.strip():
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Gemini вернула пустой ответ",
            )
        return text.strip()
