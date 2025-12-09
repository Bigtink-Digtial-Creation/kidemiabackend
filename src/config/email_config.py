from fastapi_mail import ConnectionConfig
from src.config.settings import settings

from typing import Optional


def get_mail_config() -> Optional[ConnectionConfig]:
    """
    Get email configuration. Returns None if credentials are not set.
    """
    try:
        if not all(
            [settings.MAIL_USERNAME, settings.MAIL_PASSWORD, settings.MAIL_FROM]
        ):
            print(
                "WARNING: Email credentials not configured. Email features will be disabled."
            )
            return None

        return ConnectionConfig(
            MAIL_USERNAME=settings.MAIL_USERNAME,
            MAIL_PASSWORD=settings.MAIL_PASSWORD,
            MAIL_FROM=settings.MAIL_FROM,
            MAIL_PORT=settings.MAIL_PORT,
            MAIL_SERVER=settings.MAIL_SERVER,
            MAIL_STARTTLS=settings.MAIL_STARTTLS,
            MAIL_SSL_TLS=settings.MAIL_SSL_TLS,
            USE_CREDENTIALS=settings.USE_CREDENTIALS,
            VALIDATE_CERTS=True,
        )
    except Exception as e:
        print(f"WARNING: Failed to configure email: {str(e)}")
        return None


conf = get_mail_config()
