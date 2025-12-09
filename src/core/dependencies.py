from fastapi import Depends, HTTPException, status
from src.domains.auth.models.user import User
from src.core.security import get_current_user


async def get_verified_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Dependency that ensures the current user has verified their email.
    Use this on protected routes that require email verification.
    """
    if not current_user.email_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email verification required. Please verify your email to access this resource.",
            headers={"X-Email-Verified": "false"},
        )
    return current_user
