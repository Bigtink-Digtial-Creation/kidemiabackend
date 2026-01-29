from fastapi_mail import FastMail, MessageSchema, MessageType
import secrets
from fastapi_mail import ConnectionConfig
from src.config.settings import settings
from src.config.config_service import ConfigService
from sqlalchemy.orm import Session


class EmailService:
    def __init__(self, db: Session):
        self.db = db
        self.conf = ConnectionConfig(
            MAIL_USERNAME=ConfigService.get_value(
                "smtp_username", settings.MAIL_USERNAME, db=db
            ),
            MAIL_PASSWORD=ConfigService.get_value(
                "smtp_password", settings.MAIL_PASSWORD, db=db
            ),
            MAIL_FROM=ConfigService.get_value(
                "smtp_mail_from", settings.MAIL_FROM, db=db
            ),
            MAIL_PORT=int(
                ConfigService.get_value("smtp_port", settings.MAIL_PORT, db=db)
            ),
            MAIL_SERVER=ConfigService.get_value(
                "smtp_server", settings.MAIL_SERVER, db=db
            ),
            MAIL_STARTTLS=str(
                ConfigService.get_value("MAIL_STARTTLS", settings.MAIL_STARTTLS, db=db)
            ).lower()
            == "true",
            MAIL_SSL_TLS=str(
                ConfigService.get_value("MAIL_SSL_TLS", settings.MAIL_SSL_TLS, db=db)
            ).lower()
            == "true",
            USE_CREDENTIALS=True,
            VALIDATE_CERTS=True,
        )
        self.fm = FastMail(self.conf)

    def generate_token(self) -> str:
        """Generate a secure random token"""
        return secrets.token_urlsafe(32)

    async def send_password_reset_email(
        self, email: str, token: str, client_type: str = "user"
    ):
        base_url = ConfigService.get_value(
            f"{client_type}_domain", settings.FRONTEND_URL, self.db
        )
        reset_link = f"{base_url}/auth/reset-password?token={token}"

        html = f"""
    

        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h2 style="color: #4A90E2;">Password Reset Request</h2>
                    <p>You requested to reset your password. Click the button below to reset it:</p>
                    <div style="margin: 30px 0;">
                        <a href="{reset_link}" 
                           style="background-color: #4A90E2; color: white; padding: 12px 30px; 
                                  text-decoration: none; border-radius: 5px; display: inline-block;">
                            Reset Password
                        </a>
                    </div>
                    <p>Or copy and paste this link into your browser:</p>
                    <p style="color: #666; word-break: break-all;">{reset_link}</p>
                    <p style="color: #999; font-size: 12px; margin-top: 30px;">
                        This link will expire in {settings.RESET_TOKEN_EXPIRE_MINUTES} minutes.
                        If you didn't request this, please ignore this email.
                    </p>
                </div>
            </body>
        </html>
        """

        message = MessageSchema(
            subject="Password Reset Request",
            recipients=[email],
            body=html,
            subtype=MessageType.html,
        )

        await self.fm.send_message(message)

    async def send_verification_email(
        self, email: str, token: str, client_type: str = "user"
    ):
        """Send email verification link"""
        base_url = ConfigService.get_value(
            f"{client_type}_domain", settings.FRONTEND_URL, self.db
        )
        verify_link = f"{base_url}/auth/verify-email?token={token}"
        html = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h2 style="color: #4A90E2;">Verify Your Email Address</h2>
                    <p>Thank you for registering! Please verify your email address by clicking the button below:</p>
                    <div style="margin: 30px 0;">
                        <a href="{verify_link}" 
                           style="background-color: #28a745; color: white; padding: 12px 30px; 
                                  text-decoration: none; border-radius: 5px; display: inline-block;">
                            Verify Email
                        </a>
                    </div>
                    <p>Or copy and paste this link into your browser:</p>
                    <p style="color: #666; word-break: break-all;">{verify_link}</p>
                    <p style="color: #999; font-size: 12px; margin-top: 30px;">
                        This link will expire in {settings.VERIFY_TOKEN_EXPIRE_MINUTES // 60} hours.
                    </p>
                </div>
            </body>
        </html>
        """

        message = MessageSchema(
            subject="Verify Your Email Address",
            recipients=[email],
            body=html,
            subtype=MessageType.html,
        )

        await self.fm.send_message(message)
