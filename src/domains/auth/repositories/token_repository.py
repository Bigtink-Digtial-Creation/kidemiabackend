from typing import Optional, List
from uuid import UUID
from sqlalchemy.orm import Session
from src.shared.repositories.base import BaseRepository
from src.domains.auth.models.token import RefreshToken


class RefreshTokenRepository(BaseRepository[RefreshToken, dict, dict]):
    """Repository for RefreshToken model"""

    def __init__(self, db: Session):
        super().__init__(RefreshToken, db)

    def get_by_token(self, token: str) -> Optional[RefreshToken]:
        """Get refresh token by token string"""
        return self.db.query(RefreshToken).filter(RefreshToken.token == token).first()

    def get_by_user_id(self, user_id: UUID) -> List[RefreshToken]:
        """Get all refresh tokens for a user"""
        return self.db.query(RefreshToken).filter(RefreshToken.user_id == user_id).all()

    def revoke_token(self, token: str) -> Optional[RefreshToken]:
        """Revoke a refresh token"""
        from datetime import datetime

        refresh_token = self.get_by_token(token)
        if refresh_token:
            refresh_token.is_revoked = True
            refresh_token.revoked_at = str(datetime.utcnow())
            self.db.commit()
            self.db.refresh(refresh_token)
        return refresh_token

    def revoke_all_user_tokens(self, user_id: UUID) -> int:
        """Revoke all refresh tokens for a user"""
        from datetime import datetime

        tokens = self.get_by_user_id(user_id)
        count = 0
        for token in tokens:
            if not token.is_revoked:
                token.is_revoked = True
                token.revoked_at = str(datetime.utcnow())
                count += 1
        self.db.commit()
        return count

    def clean_expired_tokens(self) -> int:
        """Delete expired tokens"""
        from datetime import datetime

        expired_tokens = (
            self.db.query(RefreshToken)
            .filter(RefreshToken.expires_at < str(datetime.utcnow()))
            .all()
        )
        count = len(expired_tokens)
        for token in expired_tokens:
            self.db.delete(token)
        self.db.commit()
        return count
