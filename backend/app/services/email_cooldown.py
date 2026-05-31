from datetime import timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import VerificationCode
from app.core.time_utils import utcnow

settings = get_settings()


def enforce_email_send_cooldown(db: Session, *, email: str, purpose: str) -> None:
    """Запрещает повторную отправку письма раньше, чем через email_send_cooldown_seconds."""
    last_sent_at = db.scalar(
        select(VerificationCode.created_at)
        .where(
            VerificationCode.email == email,
            VerificationCode.purpose == purpose,
        )
        .order_by(VerificationCode.id.desc())
        .limit(1)
    )
    if last_sent_at is None:
        return

    if last_sent_at.tzinfo is None:
        last_sent_at = last_sent_at.replace(tzinfo=timezone.utc)

    elapsed = (utcnow() - last_sent_at).total_seconds()
    cooldown = settings.email_send_cooldown_seconds
    if elapsed < cooldown:
        remaining = max(1, int(cooldown - elapsed))
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Повторная отправка возможна через {remaining} сек.",
            headers={"Retry-After": str(remaining)},
        )
