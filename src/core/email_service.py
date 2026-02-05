import secrets
import tempfile
import os
from fastapi_mail import FastMail, MessageSchema, MessageType, ConnectionConfig
from sqlalchemy.orm import Session
from typing import Optional
from src.config.settings import settings
from src.config.config_service import ConfigService
from src.shared.contants import KIDEMIA_EMAIL_BANNER
from src.shared.utils.helpers import get_client_base_url


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
            MAIL_FROM_NAME=ConfigService.get_value(
                "mail_from_name", settings.MAIL_SERVER, db=db
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

    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        file_content: Optional[bytes] = None,
        filename: Optional[str] = None,
    ):
        """Generic send email method"""
        message = MessageSchema(
            subject=subject,
            recipients=[to_email],
            body=html_content,
            subtype=MessageType.html,
        )

        message_kwargs = {
            "subject": subject,
            "recipients": [to_email],
            "body": html_content,
            "subtype": MessageType.html,
        }
        temp_file_path = None
        if file_content and filename:
            # FastAPI-Mail works best with file paths
            # Create a temporary file
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=f"_{filename}")
            temp_file.write(file_content)
            temp_file.close()
            temp_file_path = temp_file.name

            # Add attachment as file path
            message_kwargs["attachments"] = [temp_file_path]

        try:
            message = MessageSchema(**message_kwargs)
            await self.fm.send_message(message)
        finally:
            # Clean up temporary file
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.unlink(temp_file_path)
                except Exception as e:
                    # Log the error but don't fail the email send
                    print(f"Failed to delete temporary file {temp_file_path}: {e}")

    def send_password_reset_email(self, token: str, client_type: str) -> str:
        base_url = get_client_base_url(client_type=client_type)
        reset_link = f"{base_url}/auth/reset-password?token={token}"

        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {{ font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0; background-color: #f4f4f4; }}
                .container {{ max-width: 600px; margin: 20px auto; background: #ffffff; border-radius: 8px; overflow: hidden; border: 1px solid #e0e0e0; }}
                .banner {{ width: 100%; height: auto; display: block; }}
                .content {{ padding: 35px; font-size: 16px; }}
                .cta-button {{ display: inline-block; padding: 14px 28px; background-color: #F28729; color: #ffffff !important; text-decoration: none; border-radius: 6px; font-weight: bold; margin-top: 20px; text-align: center; }}
                .link-box {{ background-color: #f9fafb; padding: 15px; border-radius: 6px; border: 1px solid #eee; word-break: break-all; font-size: 13px; color: #666; margin-top: 20px; }}
                .footer {{ background-color: #f9fafb; padding: 30px; text-align: center; font-size: 13px; color: #6B7280; border-top: 1px solid #eee; }}
                .footer-links a {{ color: #BF4C20; text-decoration: none; margin: 0 10px; font-weight: 500; }}
            </style>
        </head>
        <body>
            <div class="container">
                <img src="{KIDEMIA_EMAIL_BANNER}" alt="Kidemia" class="banner">
                <div class="content">
                    <h2 style="color: #BF4C20; margin-top: 0;">Password Reset Request</h2>
                    <p>Hello,</p>
                    <p>We received a request to reset the password for your Kidemia account. If you made this request, click the button below to set a new password:</p>
                    
                    <div style="text-align: center;">
                        <a href="{reset_link}" class="cta-button">Reset My Password</a>
                    </div>

                    <p style="margin-top: 25px; font-size: 14px; color: #666;">
                        <strong>Security Note:</strong> This link will expire in {settings.RESET_TOKEN_EXPIRE_MINUTES} minutes. If you did not request a password reset, you can safely ignore this email.
                    </p>

                    <p style="font-size: 12px; color: #999; margin-top: 20px;">If the button above doesn't work, copy and paste this link into your browser:</p>
                    <div class="link-box">{reset_link}</div>
                </div>
                <div class="footer">
                    <div class="footer-links">
                        <a href="https://kidemia.net/support">Help Center</a> | 
                        <a href="https://exam.kidemia.net/auth/login">Login</a>
                    </div>
                    <p>&copy; 2026 Kidemia. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """

    def send_verification_email(self, token: str, client_type: str) -> str:
        base_url = get_client_base_url(client_type=client_type)
        verify_link = f"{base_url}/auth/verify-email?token={token}"

        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {{ font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0; background-color: #f4f4f4; }}
                .container {{ max-width: 600px; margin: 20px auto; background: #ffffff; border-radius: 8px; overflow: hidden; border: 1px solid #e0e0e0; }}
                .banner {{ width: 100%; height: auto; display: block; }}
                .content {{ padding: 35px; font-size: 16px; }}
                .cta-button {{ display: inline-block; padding: 14px 28px; background-color: #F28729; color: #ffffff !important; text-decoration: none; border-radius: 6px; font-weight: bold; margin-top: 20px; text-align: center; }}
                .link-box {{ background-color: #f9fafb; padding: 15px; border-radius: 6px; border: 1px solid #eee; word-break: break-all; font-size: 13px; color: #666; margin-top: 20px; }}
                .footer {{ background-color: #f9fafb; padding: 30px; text-align: center; font-size: 13px; color: #6B7280; border-top: 1px solid #eee; }}
                .footer-links a {{ color: #BF4C20; text-decoration: none; margin: 0 10px; font-weight: 500; }}
            </style>
        </head>
        <body>
            <div class="container">
                <img src="{KIDEMIA_EMAIL_BANNER}" alt="Kidemia" class="banner">
                <div class="content">
                    <h2 style="color: #BF4C20; margin-top: 0;">Confirm Your Email</h2>
                    <p>Welcome to Kidemia! We're excited to have you on board. To complete your registration and start using the platform, please verify your email address:</p>
                    
                    <div style="text-align: center;">
                        <a href="{verify_link}" class="cta-button">Verify Email Address</a>
                    </div>

                    <p style="margin-top: 25px; font-size: 14px; color: #666;">
                        This verification link will remain active for {settings.VERIFY_TOKEN_EXPIRE_MINUTES // 60} hours.
                    </p>

                    <p style="font-size: 12px; color: #999; margin-top: 20px;">Or copy and paste this link:</p>
                    <div class="link-box">{verify_link}</div>
                </div>
                <div class="footer">
                    <div class="footer-links">
                        <a href="https://kidemia.net/support">Support</a> | 
                        <a href="https://kidemia.net/privacy">Privacy Policy</a>
                    </div>
                    <p>&copy; 2026 Kidemia. Learning made simple.</p>
                </div>
            </div>
        </body>
        </html>
        """
