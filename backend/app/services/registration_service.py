import re
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.time_utils import utcnow
from app.core.security import (
    create_token_pair,
    generate_verification_code,
    hash_password,
    hash_verification_code,
    verify_verification_code,
)
from app.models import PendingRegistration, User, VerificationCode
from app.services.email_cooldown import enforce_email_send_cooldown
from app.services.email_service import send_verification_code_email

settings = get_settings()
USERNAME_PATTERN = re.compile(r"^[a-zA-Z0-9_]+$")
PASSWORD_PATTERN = re.compile(r"^(?=.*[A-Za-z])(?=.*\d).{8,}$")


def normalize_username(username: str) -> str:
    return username.strip()


def normalize_email(email: str) -> str:
    return email.strip().lower()


def user_username_exists(db: Session, username: str) -> bool:
    lowered = username.lower()
    return db.scalar(select(User.id).where(func.lower(User.username) == lowered).limit(1)) is not None


def user_email_exists(db: Session, email: str) -> bool:
    return db.scalar(select(User.id).where(func.lower(User.email) == email).limit(1)) is not None


def username_taken(db: Session, username: str, exclude_pending_email: Optional[str] = None) -> bool:
    if user_username_exists(db, username):
        return True

    lowered = username.lower()
    query = select(PendingRegistration.id).where(func.lower(PendingRegistration.username) == lowered)
    if exclude_pending_email:
        query = query.where(func.lower(PendingRegistration.email) != exclude_pending_email.lower())
    in_pending = db.scalar(query.limit(1))
    return in_pending is not None


def email_taken(db: Session, email: str) -> bool:
    if user_email_exists(db, email):
        return True
    in_pending = db.scalar(
        select(PendingRegistration.id).where(func.lower(PendingRegistration.email) == email).limit(1)
    )
    return in_pending is not None


def validate_username_format(username: str) -> None:
    if not USERNAME_PATTERN.match(username):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Недопустимый формат логина")


def validate_registration_fields(username: str, email: str, password: str) -> None:
    validate_username_format(username)
    if not PASSWORD_PATTERN.match(password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пароль — не менее 8 символов, буква и цифра",
        )


def _issue_verification_code(db: Session, email: str) -> str:
    enforce_email_send_cooldown(db, email=email, purpose="register")
    code = generate_verification_code()
    expires_at = utcnow() + timedelta(minutes=settings.verification_code_expire_minutes)

    db.execute(
        delete(VerificationCode).where(
            VerificationCode.email == email,
            VerificationCode.purpose == "register",
        )
    )
    db.add(
        VerificationCode(
            email=email,
            code_hash=hash_verification_code(code),
            purpose="register",
            expires_at=expires_at,
        )
    )
    return code


def request_registration_code(db: Session, *, username: str, email: str, password: str) -> None:
    username = normalize_username(username)
    email = normalize_email(email)
    validate_registration_fields(username, email, password)

    if user_email_exists(db, email):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Эта почта уже зарегистрирована")
    if username_taken(db, username, exclude_pending_email=email):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Этот логин уже занят")

    expires_at = utcnow() + timedelta(minutes=settings.pending_registration_expire_minutes)
    password_hash_value = hash_password(password)

    pending = db.scalar(select(PendingRegistration).where(PendingRegistration.email == email))
    if pending:
        pending.username = username
        pending.password_hash = password_hash_value
        pending.expires_at = expires_at
    else:
        db.add(
            PendingRegistration(
                username=username,
                email=email,
                password_hash=password_hash_value,
                expires_at=expires_at,
            )
        )

    code = _issue_verification_code(db, email)

    try:
        send_verification_code_email(to_email=email, code=code)
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Не удалось отправить письмо с кодом",
        ) from exc

    db.commit()


def resend_registration_code(db: Session, *, email: str) -> None:
    email = normalize_email(email)
    pending = db.scalar(select(PendingRegistration).where(PendingRegistration.email == email))
    if not pending:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Заявка на регистрацию не найдена")
    if pending.expires_at.replace(tzinfo=timezone.utc) < utcnow():
        db.delete(pending)
        db.commit()
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Срок регистрации истёк. Запросите код снова")

    code = _issue_verification_code(db, email)

    try:
        send_verification_code_email(to_email=email, code=code)
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Не удалось отправить письмо с кодом",
        ) from exc

    db.commit()


def complete_registration(db: Session, *, email: str, code: str) -> tuple[str, str]:
    email = normalize_email(email)
    pending = db.scalar(select(PendingRegistration).where(PendingRegistration.email == email))
    if not pending:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Заявка на регистрацию не найдена")

    pending_expires = pending.expires_at
    if pending_expires.tzinfo is None:
        pending_expires = pending_expires.replace(tzinfo=timezone.utc)
    if pending_expires < utcnow():
        db.delete(pending)
        db.commit()
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Срок регистрации истёк. Запросите код снова")

    verification = db.scalar(
        select(VerificationCode)
        .where(VerificationCode.email == email, VerificationCode.purpose == "register")
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

    if username_taken(db, pending.username, exclude_pending_email=email):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Этот логин уже занят")
    if user_email_exists(db, email):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Эта почта уже зарегистрирована")

    user = User(
        username=pending.username,
        email=pending.email,
        password_hash=pending.password_hash,
        email_verified=True,
    )
    db.add(user)
    db.flush()

    db.execute(delete(PendingRegistration).where(PendingRegistration.email == email))
    db.execute(
        delete(VerificationCode).where(
            VerificationCode.email == email,
            VerificationCode.purpose == "register",
        )
    )
    db.commit()
    db.refresh(user)

    return create_token_pair(user_id=user.id, username=user.username, email=user.email)
