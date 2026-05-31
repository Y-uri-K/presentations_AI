import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import get_settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
settings = get_settings()


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def generate_verification_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def hash_verification_code(code: str) -> str:
    payload = f"{settings.jwt_secret_key}:{code}".encode()
    return hashlib.sha256(payload).hexdigest()


def verify_verification_code(code: str, code_hash: str) -> bool:
    return hash_verification_code(code) == code_hash


def create_access_token(*, user_id: int, username: str, email: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_access_token_expire_minutes)
    payload = {
        "sub": str(user_id),
        "username": username,
        "email": email,
        "type": "access",
        "exp": expire,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_refresh_token(*, user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=settings.jwt_refresh_token_expire_days)
    payload = {
        "sub": str(user_id),
        "type": "refresh",
        "exp": expire,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_token_pair(*, user_id: int, username: str, email: str) -> tuple[str, str]:
    access = create_access_token(user_id=user_id, username=username, email=email)
    refresh = create_refresh_token(user_id=user_id)
    return access, refresh


def decode_token(token: str, *, expected_type: str) -> dict:
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise JWTError("Invalid token") from exc

    if payload.get("type") != expected_type:
        raise JWTError("Invalid token type")

    if "sub" not in payload:
        raise JWTError("Missing subject")

    return payload
