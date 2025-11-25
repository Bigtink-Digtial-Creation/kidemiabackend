from sqlalchemy import Column, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from src.shared.database.base import SimpleBaseModel


class RefreshToken(SimpleBaseModel):
    """Refresh token model for JWT refresh tokens"""

    __tablename__ = "refresh_token"

    user_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    token = Column(String(500), unique=True, nullable=False, index=True)

    expires_at = Column(String(50), nullable=False)
    is_revoked = Column(Boolean, default=False)
    revoked_at = Column(String(50), nullable=True)

    # Device information
    device_info = Column(String(500), nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)

    # Relationships
    user = relationship("User", back_populates="refresh_tokens")

    def __repr__(self):
        return f"<RefreshToken {self.id}>"


class PasswordResetToken(SimpleBaseModel):
    """Password reset token model"""

    __tablename__ = "password_reset_token"

    user_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    token = Column(String(255), unique=True, nullable=False, index=True)

    expires_at = Column(String(50), nullable=False)
    is_used = Column(Boolean, default=False)
    used_at = Column(String(50), nullable=True)

    # Relationships
    user = relationship("User")

    def __repr__(self):
        return f"<PasswordResetToken {self.id}>"


class EmailVerificationToken(SimpleBaseModel):
    """Email verification token model"""

    __tablename__ = "email_verification_token"

    user_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    token = Column(String(255), unique=True, nullable=False, index=True)

    expires_at = Column(String(50), nullable=False)
    is_used = Column(Boolean, default=False)
    used_at = Column(String(50), nullable=True)

    # Relationships
    user = relationship("User")

    def __repr__(self):
        return f"<EmailVerificationToken {self.id}>"
