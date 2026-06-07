from __future__ import annotations

from fastapi import Request

from app.config import Settings


def resolve_public_api_base_url(settings: Settings, request: Request | None = None) -> str:
    explicit = (settings.public_api_base_url or "").strip().rstrip("/")
    if explicit:
        return explicit

    for origin in settings.cors_origin_list:
        if origin.startswith("https://"):
            return origin.rstrip("/")

    if request is not None:
        forwarded_proto = request.headers.get("x-forwarded-proto")
        forwarded_host = request.headers.get("x-forwarded-host") or request.headers.get("host")
        if forwarded_host:
            scheme = (forwarded_proto or request.url.scheme or "https").split(",")[0].strip()
            host = forwarded_host.split(",")[0].strip()
            return f"{scheme}://{host}".rstrip("/")

    for origin in settings.cors_origin_list:
        return origin.rstrip("/")

    if request is not None:
        return str(request.base_url).rstrip("/")

    return ""


def build_public_api_url(settings: Settings, request: Request | None, path: str) -> str:
    base = resolve_public_api_base_url(settings, request)
    normalized_path = path if path.startswith("/") else f"/{path}"
    return f"{base}{normalized_path}"
