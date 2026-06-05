from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.core.security import create_token_pair, verify_password
from app.models import User
from app.services.registration_service import normalize_username, validate_username_format

_profile_columns_checked = False


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


def _normalize_full_name(full_name: Optional[str]) -> Optional[str]:
    if full_name is None:
        return None
    normalized = " ".join(full_name.strip().split())
    return normalized or None


def update_user_profile(
    db: Session,
    *,
    user: User,
    username: str,
    full_name: Optional[str] = None,
) -> User:
    ensure_user_profile_columns(db)
    normalized = normalize_username(username)
    validate_username_format(normalized)

    existing = db.scalar(
        select(User)
        .where(func.lower(User.username) == normalized.lower(), User.id != user.id)
        .limit(1)
    )
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Этот логин уже занят",
        )

    user.username = normalized
    user.full_name = _normalize_full_name(full_name)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def ensure_user_profile_columns(db: Session) -> None:
    global _profile_columns_checked

    if _profile_columns_checked:
        return
    if db.bind is None or db.bind.dialect.name != "mysql":
        _profile_columns_checked = True
        return

    has_full_name = db.scalar(
        text(
            """
            SELECT COUNT(*)
            FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = 'users'
              AND COLUMN_NAME = 'full_name'
            """
        )
    )
    if not has_full_name:
        db.execute(text("ALTER TABLE users ADD COLUMN full_name VARCHAR(255) NULL"))

    db.execute(text("ALTER TABLE users MODIFY profile_image LONGTEXT NULL"))
    db.commit()
    _profile_columns_checked = True


def update_user_profile_image(db: Session, *, user: User, profile_image: str) -> User:
    ensure_user_profile_columns(db)
    user.profile_image = profile_image
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def delete_user_profile_image(db: Session, *, user: User) -> User:
    user.profile_image = None
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def delete_user_account(db: Session, *, user: User) -> None:
    db.delete(user)
    db.commit()


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
