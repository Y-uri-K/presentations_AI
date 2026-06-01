from __future__ import annotations

import asyncio
import logging
from urllib.parse import urlparse

import httpx
from fastapi import HTTPException, status

from app.ai.http_errors import raise_provider_http_error
from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

_MEDIA_PATH = "/media"

_IMAGE_STYLE_SUFFIX = (
    "Pure visual illustration on white background. "
    "STRICTLY NO text, NO letters, NO numbers, NO words, NO labels, NO captions, NO typography. "
    "No people, no logos. Minimal flat icon style, muted corporate colors, 16:9."
)


def is_safety_blocked(detail: str) -> bool:
    lowered = detail.lower()
    return "safety" in lowered or "blocked" in lowered or "forbidden" in lowered


def build_slide_image_prompt(*, slide_title: str, image_hint: str | None = None) -> str:
    """Короткий нейтральный промпт на английском — реже блокируется фильтрами."""
    topic = (image_hint or slide_title).strip()
    return (
        "Abstract illustration only (symbols, shapes, charts without labels) for: "
        f"{topic}. {_IMAGE_STYLE_SUFFIX}"
    )


def build_generic_fallback_prompt() -> str:
    return (
        "Abstract geometric shapes, simple charts and nodes connected by lines, "
        f"corporate education theme. {_IMAGE_STYLE_SUFFIX}"
    )


async def generate_image_bytes(
    *,
    prompt: str,
    enable_safety_checker: bool | None = None,
) -> tuple[bytes, str]:
    if not settings.polza_api_key.strip():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Polza AI не настроен. Укажите POLZA_API_KEY в .env",
        )

    cleaned = prompt.strip()
    if not cleaned:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пустой промпт для генерации изображения",
        )

    base_url = settings.polza_base_url.rstrip("/")
    headers = {
        "Authorization": f"Bearer {settings.polza_api_key}",
        "Content-Type": "application/json",
    }
    input_payload: dict = {
        "prompt": cleaned,
        "aspect_ratio": "16:9",
    }
    if enable_safety_checker is not None:
        input_payload["enable_safety_checker"] = enable_safety_checker

    payload = {
        "model": settings.polza_image_model,
        "input": input_payload,
    }

    timeout = settings.polza_image_timeout_seconds
    poll_interval = settings.polza_image_poll_interval_seconds

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            create_response = await client.post(
                f"{base_url}{_MEDIA_PATH}",
                headers=headers,
                json=payload,
            )
            create_response.raise_for_status()
            job = create_response.json()

            job = await _wait_for_media_job(
                client=client,
                base_url=base_url,
                headers=headers,
                job=job,
                poll_interval=poll_interval,
                max_wait=timeout,
            )
            image_url = _extract_image_url(job)
            if not image_url:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="Polza AI не вернула URL изображения",
                )

            image_response = await client.get(image_url)
            image_response.raise_for_status()
            mime_type = image_response.headers.get("content-type") or _mime_from_url(image_url)
            return image_response.content, mime_type.split(";")[0].strip() or "image/png"
    except httpx.HTTPStatusError as exc:
        raise_provider_http_error("Polza AI", exc)
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Не удалось подключиться к Polza AI: {exc}",
        ) from exc


async def _wait_for_media_job(
    *,
    client: httpx.AsyncClient,
    base_url: str,
    headers: dict[str, str],
    job: dict,
    poll_interval: float,
    max_wait: float,
) -> dict:
    status_value = str(job.get("status", "")).lower()
    if status_value == "completed":
        return job
    if status_value == "failed":
        return _raise_media_failed(job)

    media_id = job.get("id")
    if not media_id:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Polza AI вернула неожиданный формат ответа",
        )

    elapsed = 0.0
    while elapsed < max_wait:
        await asyncio.sleep(poll_interval)
        elapsed += poll_interval

        status_response = await client.get(
            f"{base_url}{_MEDIA_PATH}/{media_id}",
            headers=headers,
        )
        status_response.raise_for_status()
        job = status_response.json()
        status_value = str(job.get("status", "")).lower()

        if status_value == "completed":
            return job
        if status_value == "failed":
            return _raise_media_failed(job)

    raise HTTPException(
        status_code=status.HTTP_504_GATEWAY_TIMEOUT,
        detail="Превышено время ожидания генерации изображения в Polza AI",
    )


def _raise_media_failed(job: dict) -> None:
    error = job.get("error") or {}
    message = error.get("message") if isinstance(error, dict) else str(error)
    detail = message.strip() if message else "Генерация изображения не удалась"
    logger.warning("Polza AI media failed: %s", job)
    raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=detail)


def _extract_image_url(job: dict) -> str | None:
    data = job.get("data")
    if isinstance(data, list):
        for item in data:
            url = _url_from_data_item(item)
            if url:
                return url
    elif isinstance(data, dict):
        url = _url_from_data_item(data)
        if url:
            return url

    urls = job.get("urls")
    if isinstance(urls, list) and urls:
        for item in urls:
            url = _url_from_data_item(item)
            if url:
                return url

    logger.warning(
        "Polza AI: completed без URL изображения, keys=%s data_type=%s",
        list(job.keys()),
        type(data).__name__,
    )
    return None


def _url_from_data_item(item: object) -> str | None:
    if isinstance(item, str) and item.startswith(("http://", "https://")):
        return item
    if isinstance(item, dict):
        url = item.get("url")
        if url:
            return str(url)
    return None


def _mime_from_url(url: str) -> str:
    path = urlparse(url).path.lower()
    if path.endswith(".jpg") or path.endswith(".jpeg"):
        return "image/jpeg"
    if path.endswith(".webp"):
        return "image/webp"
    return "image/png"


async def generate_slide_image_bytes(
    *,
    slide_title: str,
    image_hint: str | None = None,
) -> tuple[bytes, str]:
    """
    Генерация с повторами при блокировке safety filters.
    Не передаём полный текст презентации — только тему слайда.
    """
    attempts: list[tuple[str, str, bool | None]] = [
        ("primary", build_slide_image_prompt(slide_title=slide_title, image_hint=image_hint), None),
        ("safety_off", build_slide_image_prompt(slide_title=slide_title, image_hint=image_hint), False),
        ("generic", build_generic_fallback_prompt(), False),
    ]

    last_exc: HTTPException | None = None
    for attempt_name, attempt_prompt, safety_flag in attempts:
        try:
            result = await generate_image_bytes(
                prompt=attempt_prompt,
                enable_safety_checker=safety_flag,
            )
            if attempt_name != "primary":
                logger.info(
                    "Изображение для «%s» получено после повтора (%s)",
                    slide_title,
                    attempt_name,
                )
            return result
        except HTTPException as exc:
            last_exc = exc
            if not is_safety_blocked(str(exc.detail)):
                raise
            logger.info(
                "Polza AI: safety block для «%s», повтор (%s)",
                slide_title,
                attempt_name,
            )

    assert last_exc is not None
    raise last_exc
