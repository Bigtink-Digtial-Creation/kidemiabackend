from fastapi_mail import FastMail, MessageSchema, MessageType, ConnectionConfig
from sqlalchemy.orm import Session
import secrets

from src.config.settings import settings
from src.config.config_service import ConfigService


class EmailService:
    """Centralized email service"""

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
            MAIL_STARTTLS=True,
            MAIL_SSL_TLS=False,
            USE_CREDENTIALS=True,
            VALIDATE_CERTS=True,
        )
        self.fm = FastMail(self.conf)

    def generate_token(self) -> str:
        """Generate a secure random token"""
        return secrets.token_urlsafe(32)

    def get_client_base_url(self, client_type) -> str:
        base_url = ConfigService.get_value(
            f"{client_type}_domain", settings.FRONTEND_URL, self.db
        )

        return base_url

    async def send_email(self, to_email: str, subject: str, html_content: str):
        """Generic send email method"""
        message = MessageSchema(
            subject=subject,
            recipients=[to_email],
            body=html_content,
            subtype=MessageType.html,
        )
        await self.fm.send_message(message)

    def send_password_reset_email(
        self, db: Session, token: str, client_type: str
    ) -> str:
        base_url = ConfigService.get_value(
            f"{client_type}_domain", settings.FRONTEND_URL, db
        )
        reset_link = f"{base_url}/auth/reset-password?token={token}"

        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {{ font-family: Arial, sans-serif; background-color: #f4f6f8; margin: 0; padding: 0; }}
                .container {{ max-width: 600px; margin: 40px auto; background: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.1); }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 40px 30px; text-align: center; color: #ffffff; }}
                .content {{ padding: 40px 30px; color: #333333; line-height: 1.6; }}
                .btn {{ background-color: #667eea; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; display: inline-block; }}
                .footer {{ background-color: #f8f9fa; padding: 20px 30px; font-size: 12px; color: #999999; text-align: center; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Password Reset Request</h1>
                </div>
                <div class="content">
                    <p>You requested to reset your password. Click the button below to reset it:</p>
                    <p style="text-align:center;">
                        <a href="{reset_link}" class="btn">Reset Password</a>
                    </p>
                    <p>Or copy and paste this link into your browser:</p>
                    <p style="word-break: break-all;">{reset_link}</p>
                    <p>This link will expire in {settings.RESET_TOKEN_EXPIRE_MINUTES} minutes. If you didn't request this, ignore this email.</p>
                </div>
                <div class="footer">
                    You received this email because a password reset was requested for your account.
                </div>
            </div>
        </body>
        </html>
        """

    def send_verification_email(self, db: Session, token: str, client_type: str) -> str:
        base_url = ConfigService.get_value(
            f"{client_type}_domain", settings.FRONTEND_URL, db
        )
        verify_link = f"{base_url}/auth/verify-email?token={token}"

        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {{ font-family: Arial, sans-serif; background-color: #f4f6f8; margin: 0; padding: 0; }}
                .container {{ max-width: 600px; margin: 40px auto; background: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.1); }}
                .header {{ background: #28a745; padding: 40px 30px; text-align: center; color: #ffffff; }}
                .content {{ padding: 40px 30px; color: #333333; line-height: 1.6; }}
                .btn {{ background-color: #28a745; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; display: inline-block; }}
                .footer {{ background-color: #f8f9fa; padding: 20px 30px; font-size: 12px; color: #999999; text-align: center; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Verify Your Email Address</h1>
                </div>
                <div class="content">
                    <p>Thank you for registering! Please verify your email by clicking the button below:</p>
                    <p style="text-align:center;">
                        <a href="{verify_link}" class="btn">Verify Email</a>
                    </p>
                    <p>Or copy and paste this link into your browser:</p>
                    <p style="word-break: break-all;">{verify_link}</p>
                    <p>This link will expire in {settings.VERIFY_TOKEN_EXPIRE_MINUTES // 60} hours.</p>
                </div>
                <div class="footer">
                    You received this email because a new account was created with this email.
                </div>
            </div>
        </body>
        </html>
        """
