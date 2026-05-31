from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models import User
from app.schemas.auth import (
    AvailabilityResponse,
    LoginRequest,
    MessageResponse,
    PasswordResetConfirmRequest,
    PasswordResetRequest,
    RefreshTokenRequest,
    RegisterRequest,
    RegisterVerifyRequest,
    ResendCodeRequest,
    TokenResponse,
    UserMeResponse,
)
from app.services import auth_service, password_reset_service, registration_service as registration

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.get("/check-username", response_model=AvailabilityResponse)
def check_username(
    username: str = Query(..., min_length=3, max_length=64),
    db: Session = Depends(get_db),
):
    normalized = registration.normalize_username(username)
    registration.validate_username_format(normalized)
    return AvailabilityResponse(
        available=not registration.user_username_exists(db, normalized),
    )


@router.get("/check-email", response_model=AvailabilityResponse)
def check_email(
    email: str = Query(..., min_length=5, max_length=255),
    db: Session = Depends(get_db),
):
    normalized = registration.normalize_email(email)
    return AvailabilityResponse(available=not registration.user_email_exists(db, normalized))


@router.post("/register/request", response_model=MessageResponse)
def register_request(payload: RegisterRequest, db: Session = Depends(get_db)):
    registration.request_registration_code(
        db,
        username=payload.username,
        email=str(payload.email),
        password=payload.password,
    )
    return MessageResponse(message="Код подтверждения отправлен на почту")


@router.post("/register/resend", response_model=MessageResponse)
def register_resend(payload: ResendCodeRequest, db: Session = Depends(get_db)):
    registration.resend_registration_code(db, email=str(payload.email))
    return MessageResponse(message="Код повторно отправлен на почту")


@router.post("/register/verify", response_model=TokenResponse)
def register_verify(payload: RegisterVerifyRequest, db: Session = Depends(get_db)):
    access_token, refresh_token = registration.complete_registration(
        db,
        email=str(payload.email),
        code=payload.code,
    )
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = auth_service.authenticate_user(
        db,
        username=payload.username,
        password=payload.password,
    )
    access_token, refresh_token = auth_service.issue_tokens_for_user(user)
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=TokenResponse)
def refresh_tokens(payload: RefreshTokenRequest, db: Session = Depends(get_db)):
    access_token, refresh_token = auth_service.refresh_session(
        db,
        refresh_token=payload.refresh_token,
    )
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.get("/me", response_model=UserMeResponse)
def me(current_user: User = Depends(get_current_user)):
    return UserMeResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
    )


@router.post("/password-reset/request", response_model=MessageResponse)
def password_reset_request(payload: PasswordResetRequest, db: Session = Depends(get_db)):
    password_reset_service.request_password_reset_code(db, email=str(payload.email))
    return MessageResponse(message="Код для сброса пароля отправлен на почту")


@router.post("/password-reset/resend", response_model=MessageResponse)
def password_reset_resend(payload: PasswordResetRequest, db: Session = Depends(get_db)):
    password_reset_service.resend_password_reset_code(db, email=str(payload.email))
    return MessageResponse(message="Код повторно отправлен на почту")


@router.post("/password-reset/confirm", response_model=MessageResponse)
def password_reset_confirm(payload: PasswordResetConfirmRequest, db: Session = Depends(get_db)):
    password_reset_service.complete_password_reset(
        db,
        email=str(payload.email),
        code=payload.code,
        password=payload.password,
    )
    return MessageResponse(message="Пароль успешно изменён")
