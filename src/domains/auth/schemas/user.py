from typing import Optional, List
from uuid import UUID

from pydantic import EmailStr, Field, field_validator

from src.shared.schemas.base import (
    BaseSchema,
    CreateSchema,
    UpdateSchema,
    ResponseSchema,
    InDBSchema,
)
from src.domains.auth.enums import UserType, RoleType


class UserBase(BaseSchema):
    """Base user schema"""

    email: EmailStr
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    middle_name: Optional[str] = Field(None, max_length=100)
    phone_number: Optional[str] = Field(None, max_length=20)
    date_of_birth: Optional[str] = None
    user_type: UserType


class UserCreate(UserBase, CreateSchema):
    """Schema for creating a user"""

    password: str = Field(..., min_length=8, max_length=100)
    username: Optional[str] = Field(None, min_length=3, max_length=100)

    @field_validator("password")
    @classmethod
    def validate_password(cls, v):
        """Validate password strength"""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not any(char.isdigit() for char in v):
            raise ValueError("Password must contain at least one digit")
        if not any(char.isupper() for char in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(char.islower() for char in v):
            raise ValueError("Password must contain at least one lowercase letter")
        return v


class UserUpdate(UpdateSchema):
    """Schema for updating a user"""

    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    middle_name: Optional[str] = Field(None, max_length=100)
    phone_number: Optional[str] = Field(None, max_length=20)
    date_of_birth: Optional[str] = None
    profile_picture_url: Optional[str] = None
    bio: Optional[str] = Field(None, max_length=1000)
    language: Optional[str] = None
    timezone: Optional[str] = None


class UserResponse(UserBase, ResponseSchema):
    """Schema for user response"""

    username: Optional[str]
    is_active: bool
    is_verified: bool
    is_email_verified: bool
    profile_picture_url: Optional[str]
    bio: Optional[str]
    language: str
    timezone: str
    last_login: Optional[str]
    roles: List["RoleResponse"] = []

    @property
    def full_name(self) -> str:
        """Get full name"""
        parts = [self.first_name]
        if self.middle_name:
            parts.append(self.middle_name)
        parts.append(self.last_name)
        return " ".join(parts)


class UserInDB(UserResponse, InDBSchema):
    """Schema for user in database"""

    password_hash: str
    two_factor_enabled: bool
    two_factor_secret: Optional[str]


class LoginRequest(BaseSchema):
    """Schema for login request"""

    email: EmailStr
    password: str = Field(..., min_length=1)
    remember_me: bool = False


class LoginResponse(BaseSchema):
    """Schema for login response"""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse


class RegisterRequest(UserCreate):
    """Schema for registration request"""

    pass


class RegisterResponse(BaseSchema):
    """Schema for registration response"""

    message: str
    user: UserResponse


class TokenResponse(BaseSchema):
    """Schema for token response"""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshTokenRequest(BaseSchema):
    """Schema for refresh token request"""

    refresh_token: str


class ChangePasswordRequest(BaseSchema):
    """Schema for password change request"""

    current_password: str
    new_password: str = Field(..., min_length=8, max_length=100)

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v):
        """Validate password strength"""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not any(char.isdigit() for char in v):
            raise ValueError("Password must contain at least one digit")
        if not any(char.isupper() for char in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(char.islower() for char in v):
            raise ValueError("Password must contain at least one lowercase letter")
        return v


class ForgotPasswordRequest(BaseSchema):
    """Schema for forgot password request"""

    email: EmailStr


class ResetPasswordRequest(BaseSchema):
    """Schema for password reset request"""

    token: str
    new_password: str = Field(..., min_length=8, max_length=100)


class VerifyEmailRequest(BaseSchema):
    """Schema for email verification request"""

    token: str


class RoleBase(BaseSchema):
    """Base role schema"""

    name: str = Field(..., min_length=1, max_length=100)
    display_name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    role_type: RoleType


class RoleCreate(RoleBase, CreateSchema):
    """Schema for creating a role"""

    permission_ids: List[UUID] = []


class RoleUpdate(UpdateSchema):
    """Schema for updating a role"""

    display_name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    permission_ids: Optional[List[UUID]] = None


class RoleResponse(RoleBase, ResponseSchema):
    """Schema for role response"""

    is_system: bool
    permissions: List["PermissionResponse"] = []


class PermissionBase(BaseSchema):
    """Base permission schema"""

    name: str = Field(..., min_length=1, max_length=100)
    display_name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    resource: str = Field(..., min_length=1, max_length=100)
    action: str = Field(..., min_length=1, max_length=50)


class PermissionCreate(PermissionBase, CreateSchema):
    """Schema for creating a permission"""

    pass


class PermissionUpdate(UpdateSchema):
    """Schema for updating a permission"""

    display_name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)


class PermissionResponse(PermissionBase, ResponseSchema):
    """Schema for permission response"""

    pass


class AssignRolesToUserRequest(BaseSchema):
    """Schema for assigning roles to user"""

    role_ids: List[UUID] = Field(..., min_items=1)


class AssignPermissionsToRoleRequest(BaseSchema):
    """Schema for assigning permissions to role"""

    permission_ids: List[UUID] = Field(..., min_items=1)


# Update forward references
UserResponse.model_rebuild()
RoleResponse.model_rebuild()
