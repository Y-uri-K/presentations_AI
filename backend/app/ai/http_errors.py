from __future__ import annotations

import json

import httpx
from fastapi import HTTPException, status


def raise_provider_http_error(provider_name: str, exc: httpx.HTTPStatusError) -> None:
    status_code = exc.response.status_code
    body_text = exc.response.text
    message = _extract_error_message(body_text)

    if status_code == 429:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                f"Исчерпана квота {provider_name}. "
                "Подождите и повторите позже или выберите другой ИИ (MiMo / Ollama)."
            ),
        ) from exc

    if status_code in (401, 403):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Ошибка авторизации {provider_name}. Проверьте API-ключ в .env.",
        ) from exc

    if message and "quota" in message.lower():
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                f"Исчерпана квота {provider_name}. "
                "Выберите другой ИИ (MiMo / Ollama) или обновите тариф."
            ),
        ) from exc

    snippet = body_text[:240] if body_text else str(exc)
    raise HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail=f"{provider_name}: {snippet}",
    ) from exc


def _extract_error_message(body_text: str) -> str:
    try:
        data = json.loads(body_text)
    except json.JSONDecodeError:
        return body_text

    if isinstance(data, dict):
        error = data.get("error")
        if isinstance(error, dict) and isinstance(error.get("message"), str):
            return error["message"]
        if isinstance(data.get("message"), str):
            return data["message"]
        detail = data.get("detail")
        if isinstance(detail, str):
            return detail
    return body_text
