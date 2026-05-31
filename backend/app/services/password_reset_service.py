from datetime import timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.security import (
    generate_verification_code,
    hash_password,
    hash_verification_code,
    verify_verification_code,
)
from app.models import User, VerificationCode
from app.services.email_cooldown import enforce_email_send_cooldown
from app.services.email_service import send_password_reset_code_email
from app.core.time_utils import utcnow
from app.services.registration_service import (
    PASSWORD_PATTERN,
    normalize_email,
    user_email_exists,
)

settings = get_settings()
PURPOSE_PASSWORD_RESET = "password_reset"


def validate_password_format(password: str) -> None:
    if not PASSWORD_PATTERN.match(password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пароль — не менее 8 символов, буква и цифра",
        )


def _get_user_by_email(db: Session, email: str) -> User:
    user = db.scalar(select(User).where(func.lower(User.email) == email).limit(1))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Почта не зарегистрирована",
        )
    return user


def _issue_reset_code(db: Session, email: str) -> str:
    enforce_email_send_cooldown(db, email=email, purpose=PURPOSE_PASSWORD_RESET)
    code = generate_verification_code()
    expires_at = utcnow() + timedelta(minutes=settings.verification_code_expire_minutes)

    db.execute(
        delete(VerificationCode).where(
            VerificationCode.email == email,
            VerificationCode.purpose == PURPOSE_PASSWORD_RESET,
        )
    )
    db.add(
        VerificationCode(
            email=email,
            code_hash=hash_verification_code(code),
            purpose=PURPOSE_PASSWORD_RESET,
            expires_at=expires_at,
        )
    )
    return code


def _send_reset_code(db: Session, email: str) -> None:
    code = _issue_reset_code(db, email)
    try:
        send_password_reset_code_email(to_email=email, code=code)
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Не удалось отправить письмо с кодом",
        ) from exc
    db.commit()


def request_password_reset_code(db: Session, *, email: str) -> None:
    email = normalize_email(email)
    if not user_email_exists(db, email):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Почта не зарегистрирована",
        )
    _send_reset_code(db, email)


def resend_password_reset_code(db: Session, *, email: str) -> None:
    request_password_reset_code(db, email=email)


def complete_password_reset(db: Session, *, email: str, code: str, password: str) -> None:
    email = normalize_email(email)
    validate_password_format(password)

    user = _get_user_by_email(db, email)

    verification = db.scalar(
        select(VerificationCode)
        .where(
            VerificationCode.email == email,
            VerificationCode.purpose == PURPOSE_PASSWORD_RESET,
        )
        .order_by(VerificationCode.id.desc())
        .limit(1)
    )
    if not verification:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Код подтверждения не найден")

    code_expires = verification.expires_at
    if code_expires.tzinfo is None:
        code_expires = code_expires.replace(tzinfo=timezone.utc)
    if code_expires < utcnow():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Срок действия кода истёк")

    if not verify_verification_code(code, verification.code_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Неверный код подтверждения")

    user.password_hash = hash_password(password)
    db.execute(
        delete(VerificationCode).where(
            VerificationCode.email == email,
            VerificationCode.purpose == PURPOSE_PASSWORD_RESET,
        )
    )
    db.commit()
