import logging
import smtplib
from email.message import EmailMessage

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def send_verification_code_email(*, to_email: str, code: str) -> None:
    subject = "AIDeck — код подтверждения регистрации"
    body = (
        f"Ваш код подтверждения: {code}\n\n"
        f"Код действителен {settings.verification_code_expire_minutes} мин.\n"
        "Если вы не регистрировались в AIDeck, проигнорируйте это письмо."
    )

    if settings.email_dev_mode:
        logger.info("[EMAIL_DEV_MODE] Код для %s: %s", to_email, code)
        print(f"[EMAIL_DEV_MODE] Verification code for {to_email}: {code}")
        return

    if not settings.smtp_host:
        raise RuntimeError("SMTP не настроен. Укажите SMTP_* в .env или включите EMAIL_DEV_MODE=true")

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = settings.smtp_from
    message["To"] = to_email
    message.set_content(body)

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as server:
        if settings.smtp_use_tls:
            server.starttls()
        if settings.smtp_user:
            server.login(settings.smtp_user, settings.smtp_password)
        server.send_message(message)
