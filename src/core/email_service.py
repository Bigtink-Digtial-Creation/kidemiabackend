from fastapi_mail import FastMail, MessageSchema, MessageType
import secrets
from src.config.email_config import conf
from src.config.settings import settings


class EmailService:
    def __init__(self):
        self.fm = FastMail(conf)

    def generate_token(self) -> str:
        """Generate a secure random token"""
        return secrets.token_urlsafe(32)

    async def send_password_reset_email(self, email: str, token: str):
        """Send password reset email"""
        reset_link = f"{settings.FRONTEND_URL}/reset-password?token={token}"

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

    async def send_verification_email(self, email: str, token: str):
        """Send email verification link"""
        verify_link = f"{settings.FRONTEND_URL}/verify-email?token={token}"

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


email_service = EmailService()
