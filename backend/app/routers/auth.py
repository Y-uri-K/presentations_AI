from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.auth import (
    AvailabilityResponse,
    MessageResponse,
    RegisterRequest,
    RegisterVerifyRequest,
    ResendCodeRequest,
    TokenResponse,
)
from app.services import registration_service as registration

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
    token = registration.complete_registration(
        db,
        email=str(payload.email),
        code=payload.code,
    )
    return TokenResponse(access_token=token)
