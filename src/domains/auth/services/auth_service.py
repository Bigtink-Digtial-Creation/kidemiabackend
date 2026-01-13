from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from src.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
)
from src.core.exceptions import (
    InvalidCredentialsException,
    ResourceNotFoundException,
    ResourceAlreadyExistsException,
    AccountDisabledException,
    TokenExpiredException,
    InvalidTokenException,
)
from src.domains.auth.repositories.user_repository import UserRepository

from src.domains.auth.repositories.role_repository import RoleRepository
from src.domains.auth.repositories.token_repository import RefreshTokenRepository

from src.domains.auth.schemas.user import (
    UserResponse,
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    TokenResponse,
)

from src.domains.auth.schemas.user import ChangePasswordRequest
from src.domains.auth.models.user import User
from src.shared.events.dispatcher import dispatch_user_registered

# from src.domains.auth.models.token import RefreshToken
from src.core.email_service import EmailService
from src.shared.utils.helpers import determine_client_type
from src.config.settings import settings


class AuthService:
    """Service for authentication operations"""

    def __init__(self, db: Session):
        self.db = db
        self.user_repo = UserRepository(db)
        self.role_repo = RoleRepository(db)
        self.token_repo = RefreshTokenRepository(db)

    async def register(
        self,
        user_data: RegisterRequest,
        assign_default_role: bool = True,
    ) -> UserResponse:
        """
        Register a new user or reactivate a soft-deleted one
        """
        email_service = EmailService(self.db)

        # 🔹 Fetch by email (do NOT just check existence)
        existing_user = self.user_repo.get_by_email(user_data.email)

        # -----------------------------
        # CASE 1: User exists and is ACTIVE
        # -----------------------------
        if existing_user and existing_user.deleted_at is None:
            raise ResourceAlreadyExistsException("User", f"email '{user_data.email}'")

        # -----------------------------
        # CASE 2: User exists but is SOFT-DELETED → REACTIVATE
        # -----------------------------
        if existing_user and existing_user.deleted_at is not None:
            # Optional username check (only if changed)
            if (
                user_data.username
                and user_data.username != existing_user.username
                and self.user_repo.username_exists(user_data.username)
            ):
                raise ResourceAlreadyExistsException(
                    "User", f"username '{user_data.username}'"
                )

            # Reactivate account
            existing_user.deleted_at = None
            existing_user.is_active = True
            existing_user.is_email_verified = False
            existing_user.is_deleted = False
            existing_user.password_hash = hash_password(user_data.password)

            # Regenerate email verification
            verify_token = email_service.generate_token()
            existing_user.email_verification_token = verify_token
            existing_user.email_verification_token_expires = (
                datetime.utcnow()
                + timedelta(minutes=settings.VERIFY_TOKEN_EXPIRE_MINUTES)
            )

            # Update optional fields
            update_data = user_data.model_dump(
                exclude={
                    "password",
                    "category",
                    "guardian_email",
                    "school_name",
                    "admin_email",
                },
                exclude_none=True,
            )

            for key, value in update_data.items():
                setattr(existing_user, key, value)

            self.user_repo.save(existing_user)

            # Ensure default role exists
            if assign_default_role:
                default_role_name = f"{user_data.user_type}"
                default_role = self.role_repo.get_by_name(default_role_name)
                if default_role:
                    self.user_repo.add_role(existing_user.id, default_role.id)

            dispatch_user_registered(
                user_id=existing_user.id,
                user_type=user_data.user_type,
                registration_data=user_data,
            )

            try:
                client_type = determine_client_type(existing_user)
                await email_service.send_verification_email(
                    existing_user.email, verify_token, client_type
                )
            except Exception as e:
                print(f"Failed to send verification email: {str(e)}")

            return UserResponse.model_validate(existing_user)

        # -----------------------------
        # CASE 3: Brand new user
        # -----------------------------
        if user_data.username and self.user_repo.username_exists(user_data.username):
            raise ResourceAlreadyExistsException(
                "User", f"username '{user_data.username}'"
            )

        password_hash = hash_password(user_data.password)

        user_dict = user_data.model_dump(
            exclude={
                "password",
                "category",
                "guardian_email",
                "school_name",
                "admin_email",
            }
        )
        user_dict["password_hash"] = password_hash

        user = self.user_repo.create(user_dict)

        verify_token = email_service.generate_token()
        user.email_verification_token = verify_token
        user.email_verification_token_expires = datetime.utcnow() + timedelta(
            minutes=settings.VERIFY_TOKEN_EXPIRE_MINUTES
        )

        if assign_default_role:
            default_role_name = f"{user_data.user_type}"
            default_role = self.role_repo.get_by_name(default_role_name)
            if default_role:
                self.user_repo.add_role(user.id, default_role.id)

        dispatch_user_registered(
            user_id=user.id,
            user_type=user_data.user_type,
            registration_data=user_data,
        )

        try:
            client_type = determine_client_type(user)
            await email_service.send_verification_email(
                user.email, verify_token, client_type
            )
        except Exception as e:
            print(f"Failed to send verification email: {str(e)}")

        return UserResponse.model_validate(user)

    async def register2(
        self, user_data: RegisterRequest, assign_default_role: bool = True
    ) -> UserResponse:
        """
        Register a new user

        Args:
            user_data: User registration data
            assign_default_role: Whether to assign default role


        Returns:
            UserResponse: Created user

        Raises:
            ResourceAlreadyExistsException: If email or username exists
        """
        email_service = EmailService(self.db)

        if self.user_repo.email_exists(user_data.email):
            raise ResourceAlreadyExistsException("User", f"email '{user_data.email}'")

        if user_data.username and self.user_repo.username_exists(user_data.username):
            raise ResourceAlreadyExistsException(
                "User", f"username '{user_data.username}'"
            )

        password_hash = hash_password(user_data.password)

        user_dict = user_dict = user_data.model_dump(
            exclude={
                "password",
                "category",
                "guardian_email",
                "school_name",
                "admin_email",
            }
        )
        user_dict["password_hash"] = password_hash

        user = self.user_repo.create(user_dict)

        verify_token = email_service.generate_token()
        token_expires = datetime.utcnow() + timedelta(
            minutes=settings.VERIFY_TOKEN_EXPIRE_MINUTES
        )
        user.email_verification_token = verify_token
        user.email_verification_token_expires = token_expires

        if assign_default_role:
            default_role_name = f"{user_data.user_type}"
            default_role = self.role_repo.get_by_name(default_role_name)
            if default_role:
                self.user_repo.add_role(user.id, default_role.id)

        dispatch_user_registered(
            user_id=user.id,
            user_type=user_data.user_type,
            registration_data=user_data,
        )

        try:
            client_type = determine_client_type(user)
            await email_service.send_verification_email(
                user.email, verify_token, client_type
            )
        except Exception as e:
            print(f"Failed to send verification email: {str(e)}")

        return UserResponse.model_validate(user)

    async def login(
        self,
        login_data: LoginRequest,
        device_info: Optional[dict] = None,
    ) -> LoginResponse:
        """
        Authenticate user and return tokens
        """

        # 🔹 Fetch user (including deleted)
        user = self.user_repo.get_by_email(login_data.email)

        if not user:
            raise InvalidCredentialsException()

        if user.deleted_at is not None:
            raise AccountDisabledException()

        if user.locked_until:
            locked_until = (
                user.locked_until
                if isinstance(user.locked_until, datetime)
                else datetime.fromisoformat(user.locked_until)
            )

            if datetime.now(timezone.utc) < locked_until:
                raise AccountDisabledException()
            else:
                self.user_repo.reset_failed_login(user.id)

        if not verify_password(login_data.password, user.password_hash):
            self.user_repo.increment_failed_login(user.id)
            raise InvalidCredentialsException()

        if not user.is_active:
            raise AccountDisabledException()

        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        refresh_token_expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

        token_claims = {
            "user_type": user.user_type.value,
            "email": user.email,
            "roles": [role.name for role in user.roles],
            "permissions": [
                perm.name for role in user.roles for perm in role.permissions
            ],
        }

        access_token = create_access_token(
            subject=user.id,
            expires_delta=access_token_expires,
            additional_claims=token_claims,
        )

        refresh_token = create_refresh_token(
            subject=user.id,
            expires_delta=refresh_token_expires,
        )

        self.token_repo.create(
            {
                "user_id": user.id,
                "token": refresh_token,
                "expires_at": datetime.now(timezone.utc) + refresh_token_expires,
                "device_info": str(device_info) if device_info else None,
                "ip_address": device_info.get("ip_address") if device_info else None,
                "user_agent": device_info.get("user_agent") if device_info else None,
            }
        )

        self.user_repo.update_last_login(user.id)
        self.user_repo.reset_failed_login(user.id)

        return LoginResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=int(access_token_expires.total_seconds()),
            user=UserResponse.model_validate(user),
        )

    # Inside AuthService class

    async def admin_login(
        self,
        login_data: LoginRequest,
        device_info: Optional[dict] = None,
    ) -> LoginResponse:
        """
        Authenticate user and verify they have administrative privileges
        """
        user = self.user_repo.get_by_email(login_data.email)

        if not user:
            raise InvalidCredentialsException()
        forbidden_types = ["guardian", "student"]
        if user.user_type.value in forbidden_types:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User account not found"
            )
        return await self.login(login_data, device_info)

    async def login2(
        self, login_data: LoginRequest, device_info: Optional[dict] = None
    ) -> LoginResponse:
        """
        Authenticate user and return tokens

        Args:
            login_data: Login credentials
            device_info: Device information for token tracking

        Returns:
            LoginResponse: Access and refresh tokens with user info

        Raises:
            InvalidCredentialsException: If credentials are invalid
            AccountDisabledException: If account is disabled
        """
        # Get user by email
        user = self.user_repo.get_by_email(login_data.email)

        if not user:
            raise InvalidCredentialsException()

        # Check if account is locked
        if user.locked_until:
            locked_until = datetime.fromisoformat(user.locked_until)
            if datetime.now(timezone.utc) < locked_until:
                raise AccountDisabledException()
            else:
                # Unlock account
                self.user_repo.reset_failed_login(user.id)

        # Verify password
        if not verify_password(login_data.password, user.password_hash):
            self.user_repo.increment_failed_login(user.id)
            raise InvalidCredentialsException()

        # Check if account is active
        if not user.is_active:
            raise AccountDisabledException()

        # Generate tokens
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        refresh_token_expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

        # Prepare token claims
        token_claims = {
            "user_type": user.user_type.value,
            "email": user.email,
            "roles": [role.name for role in user.roles],
            "permissions": [
                perm.name for role in user.roles for perm in role.permissions
            ],
        }

        access_token = create_access_token(
            subject=user.id,
            expires_delta=access_token_expires,
            additional_claims=token_claims,
        )

        refresh_token = create_refresh_token(
            subject=user.id, expires_delta=refresh_token_expires
        )

        # Store refresh token
        refresh_token_data = {
            "user_id": user.id,
            "token": refresh_token,
            "expires_at": str(datetime.now(timezone.utc) + refresh_token_expires),
            "device_info": str(device_info) if device_info else None,
            "ip_address": device_info.get("ip_address") if device_info else None,
            "user_agent": device_info.get("user_agent") if device_info else None,
        }
        self.token_repo.create(refresh_token_data)

        # Update last login
        self.user_repo.update_last_login(user.id)
        self.user_repo.reset_failed_login(user.id)

        return LoginResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=int(access_token_expires.total_seconds()),
            user=UserResponse.model_validate(user),
        )

    async def refresh_access_token(self, refresh_token: str) -> TokenResponse:
        """
        Refresh access token using refresh token

        Args:
            refresh_token: Refresh token

        Returns:
            TokenResponse: New access and refresh tokens

        Raises:
            InvalidTokenException: If token is invalid
            TokenExpiredException: If token is expired
        """
        # Get refresh token from database
        token_record = self.token_repo.get_by_token(refresh_token)

        if not token_record:
            raise InvalidTokenException()

        # Check if token is revoked
        if token_record.is_revoked:
            raise InvalidTokenException()

        # Check if token is expired
        expires_at = datetime.fromisoformat(token_record.expires_at)
        if datetime.now(timezone.utc) > expires_at:
            raise TokenExpiredException()

        # Get user
        user = self.user_repo.get_by_id(token_record.user_id)
        if not user or not user.is_active:
            raise InvalidTokenException()

        # Generate new tokens
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        refresh_token_expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

        token_claims = {
            "user_type": user.user_type.value,
            "email": user.email,
            "roles": [role.name for role in user.roles],
            "permissions": [
                perm.name for role in user.roles for perm in role.permissions
            ],
        }

        new_access_token = create_access_token(
            subject=user.id,
            expires_delta=access_token_expires,
            additional_claims=token_claims,
        )

        new_refresh_token = create_refresh_token(
            subject=user.id, expires_delta=refresh_token_expires
        )

        # Revoke old refresh token
        self.token_repo.revoke_token(refresh_token)

        # Store new refresh token
        refresh_token_data = {
            "user_id": user.id,
            "token": new_refresh_token,
            "expires_at": str(datetime.now(timezone.utc) + refresh_token_expires),
            "device_info": token_record.device_info,
            "ip_address": token_record.ip_address,
            "user_agent": token_record.user_agent,
        }
        self.token_repo.create(refresh_token_data)

        return TokenResponse(
            access_token=new_access_token,
            refresh_token=new_refresh_token,
            token_type="bearer",
            expires_in=int(access_token_expires.total_seconds()),
        )

    async def logout(self, refresh_token: str) -> bool:
        """
        Logout user by revoking refresh token

        Args:
            refresh_token: Refresh token to revoke

        Returns:
            bool: True if successful
        """
        self.token_repo.revoke_token(refresh_token)
        return True

    async def logout_all_devices(self, user_id: UUID) -> int:
        """
        Logout user from all devices

        Args:
            user_id: User ID

        Returns:
            int: Number of tokens revoked
        """
        return self.token_repo.revoke_all_user_tokens(user_id)

    async def change_password(
        self, user_id: UUID, password_data: ChangePasswordRequest
    ) -> bool:
        """
        Change user password

        Args:
            user_id: User ID
            password_data: Password change data

        Returns:
            bool: True if successful

        Raises:
            ResourceNotFoundException: If user not found
            InvalidCredentialsException: If current password is incorrect
        """
        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise ResourceNotFoundException("User", user_id)

        # Verify current password
        if not verify_password(password_data.current_password, user.password_hash):
            raise InvalidCredentialsException()

        # Hash new password
        new_password_hash = hash_password(password_data.new_password)

        # Update password
        self.user_repo.update(user_id, {"password_hash": new_password_hash})

        # Revoke all refresh tokens (force re-login on all devices)
        self.token_repo.revoke_all_user_tokens(user_id)

        return True

    async def verify_token(self, token: str) -> Optional[User]:
        """
        Verify token and return user

        Args:
            token: Access token

        Returns:
            Optional[User]: User if token is valid
        """
        from src.core.security import decode_token

        try:
            payload = decode_token(token)
            user_id = UUID(payload.get("sub"))
            user = self.user_repo.get_by_id(user_id)
            return user if user and user.is_active else None
        except Exception:
            return None
