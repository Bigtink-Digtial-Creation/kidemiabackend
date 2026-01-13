from datetime import datetime, timedelta, timezone
from typing import Optional, Union
from uuid import UUID
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from jose import jwt, JWTError
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from src.domains.auth.models.user import User
from src.config.database import get_db
from src.config.settings import settings
from cryptography.fernet import Fernet
import base64
import hashlib


def get_encryption_key() -> bytes:
    key_bytes = settings.SECRET_KEY.encode()
    hash_key = hashlib.sha256(key_bytes).digest()
    return base64.urlsafe_b64encode(hash_key)


def encrypt_value(value: str) -> str:
    """Encrypt a sensitive value"""

    key = get_encryption_key()
    f = Fernet(key)
    encrypted = f.encrypt(value.encode())
    return encrypted.decode()


def decrypt_value(encrypted_value: str) -> str:
    """Decrypt a sensitive value"""
    key = get_encryption_key()
    f = Fernet(key)
    decrypted = f.decrypt(encrypted_value.encode())
    return decrypted.decode()


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    password_bytes = password.encode("utf-8")[:72]
    return pwd_context.hash(password_bytes.decode("utf-8", errors="ignore"))


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    password_bytes = plain_password.encode("utf-8")[:72]
    return pwd_context.verify(
        password_bytes.decode("utf-8", errors="ignore"), hashed_password
    )


security = HTTPBearer()


def create_access_token(
    subject: Union[str, UUID],
    expires_delta: Optional[timedelta] = None,
    additional_claims: Optional[dict] = None,
) -> str:
    """
    Create JWT access token

    Args:
        subject: User ID or identifier
        expires_delta: Token expiration time
        additional_claims: Additional data to include in token
    """
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode = {"exp": expire, "sub": str(subject), "type": "access"}

    if additional_claims:
        to_encode.update(additional_claims)

    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def create_refresh_token(
    subject: Union[str, UUID], expires_delta: Optional[timedelta] = None
) -> str:
    """Create JWT refresh token"""
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            days=settings.REFRESH_TOKEN_EXPIRE_DAYS
        )

    to_encode = {"exp": expire, "sub": str(subject), "type": "refresh"}

    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def decode_token(token: str) -> dict:
    """
    Decode and validate JWT token

    Raises:
        HTTPException: If token is invalid or expired
    """
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_token_payload(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """
    FastAPI dependency to extract and validate token payload

    Usage:
        @app.get("/protected")
        def protected_route(payload: dict = Depends(get_token_payload)):
            user_id = payload.get("sub")
    """
    token = credentials.credentials
    payload = decode_token(token)

    # Verify it's an access token
    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type"
        )

    return payload


def get_refresh_token_payload(token: str) -> dict:
    payload = decode_token(token)
    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )
    return payload


def get_current_user_id(payload: dict = Depends(get_token_payload)) -> UUID:
    """
    FastAPI dependency to get current user ID from token

    Usage:
        @app.get("/me")
        def get_me(user_id: UUID = Depends(get_current_user_id)):
            return {"user_id": user_id}
    """
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload"
        )

    try:
        return UUID(user_id)
    except (ValueError, AttributeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user ID in token"
        )


def get_current_user(
    user_id: UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> User:
    """
    FastAPI dependency to get the current authenticated user
    """

    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    return user


def get_current_admin(payload: dict = Depends(get_token_payload)) -> str:
    """
    Verify that current user is an admin.
    Raises HTTPException if user is not admin.
    """
    user_role = payload.get("role")
    if not user_role:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload"
        )

    print(user_role)
    if user_role != "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required"
        )

    return user_role


def require_permissions(*required_permissions: str):
    """
    Decorator/dependency to check if user has required permissions

    Usage:
        @app.get("/admin")
        def admin_route(
            user_id: UUID = Depends(get_current_user_id),
            _: None = Depends(require_permissions("admin:read", "admin:write"))
        ):
            return {"message": "Admin access granted"}
    """

    def permission_checker(payload: dict = Depends(get_token_payload)):
        user_permissions = payload.get("permissions", [])

        for permission in required_permissions:
            if permission not in user_permissions:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission denied. Required: {permission}",
                )

        return None

    # return Depends(permission_checker)
    return permission_checker


def require_roles(*required_roles: str):
    """
    Decorator/dependency to check if user has required roles

    Usage:
        @app.get("/admin")
        def admin_route(
            user_id: UUID = Depends(get_current_user_id),
            _: None = Depends(require_roles("admin", "superadmin"))
        ):
            return {"message": "Admin access granted"}
    """

    def role_checker(payload: dict = Depends(get_token_payload)):
        user_roles = payload.get("roles", [])

        if not any(role in user_roles for role in required_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {', '.join(required_roles)}",
            )

        return None

    # return Depends(role_checker)
    return role_checker


class APIKeyValidator:
    """Validate API keys for service-to-service communication"""

    def __init__(self, api_key_header: str = "X-API-Key"):
        self.api_key_header = api_key_header

    async def __call__(self, api_key: str = Depends(HTTPBearer())):
        """Validate API key"""

        valid_keys = [settings.API_KEY]
        if settings.API_KEY_SECONDARY:
            valid_keys.append(settings.API_KEY_SECONDARY)

        if api_key not in valid_keys:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key"
            )

        return api_key
