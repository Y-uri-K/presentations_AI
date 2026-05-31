from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.security import create_token_pair, verify_password
from app.models import User
from app.services.registration_service import normalize_username


def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    return db.get(User, user_id)


def get_user_by_username(db: Session, username: str) -> Optional[User]:
    normalized = normalize_username(username)
    return db.scalar(
        select(User).where(func.lower(User.username) == normalized.lower()).limit(1)
    )


def authenticate_user(db: Session, *, username: str, password: str) -> User:
    user = get_user_by_username(db, username)
    if user is None or not verify_password(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Логин или пароль неправильные",
        )
    return user


def issue_tokens_for_user(user: User) -> tuple[str, str]:
    return create_token_pair(user_id=user.id, username=user.username, email=user.email)


def refresh_session(db: Session, *, refresh_token: str) -> tuple[str, str]:
    from app.core.security import decode_token
    from jose import JWTError

    try:
        payload = decode_token(refresh_token, expected_type="refresh")
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Недействительный или просроченный refresh-токен",
        ) from None

    user = get_user_by_id(db, int(payload["sub"]))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Пользователь не найден",
        )
    return issue_tokens_for_user(user)
