import base64

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
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
    UpdateProfileRequest,
    UserMeResponse,
)
from app.services import auth_service, password_reset_service, registration_service as registration

router = APIRouter(prefix="/api/auth", tags=["auth"])

MAX_PROFILE_IMAGE_BYTES = 2 * 1024 * 1024


def _user_response(user: User) -> UserMeResponse:
    return UserMeResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        profile_image=user.profile_image,
        role="user",
    )


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
    return _user_response(current_user)


@router.patch("/me", response_model=UserMeResponse)
def update_me(
    payload: UpdateProfileRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user = auth_service.update_user_profile(db, user=current_user, username=payload.username)
    return _user_response(user)


@router.post("/me/profile-image", response_model=UserMeResponse)
async def update_profile_image(
    image: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if image.content_type not in {"image/jpeg", "image/png", "image/webp", "image/gif"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Загрузите изображение JPG, PNG, WEBP или GIF",
        )

    content = await image.read()
    if len(content) > MAX_PROFILE_IMAGE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Файл профиля должен быть не больше 2 МБ",
        )

    encoded = base64.b64encode(content).decode("ascii")
    data_url = f"data:{image.content_type};base64,{encoded}"
    user = auth_service.update_user_profile_image(
        db,
        user=current_user,
        profile_image=data_url,
    )
    return _user_response(user)


@router.delete("/me", response_model=MessageResponse)
def delete_me(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    auth_service.delete_user_account(db, user=current_user)
    return MessageResponse(message="Аккаунт удалён")


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
