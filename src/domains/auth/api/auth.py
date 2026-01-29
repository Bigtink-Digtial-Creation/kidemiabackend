from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from src.config.database import get_db
from src.core.security import get_current_user_id, require_roles
from src.domains.auth.enums import UserType
from src.domains.auth.schemas.guardian import GuardianRegisterRequest
from src.domains.auth.services.auth_service import AuthService
from src.domains.auth.schemas.user import (
    RegisterRequest,
    RegisterResponse,
    LoginRequest,
    LoginResponse,
    RefreshTokenRequest,
    TokenResponse,
    ChangePasswordRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    VerifyEmailRequest,
)
from src.domains.auth.models.user import User
from src.domains.auth.services.user_service import UserService
from src.domains.auth.schemas.user import (
    UserUpdate,
    UserResponse,
)
from src.shared.schemas.base import MessageResponse, SuccessResponse
from src.config.settings import settings
from src.core.security import hash_password
from src.core.email_service import EmailService
from src.shared.utils.helpers import determine_client_type

router = APIRouter()


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
async def register(user_data: RegisterRequest, db: Session = Depends(get_db)):
    """
    Register a new user account.

    - **email**: Valid email address
    - **password**: Min 8 characters with uppercase, lowercase, and number
    - **first_name**: User's first name
    - **last_name**: User's last name
    - **user_type**: Type of user (student, guardian, institution_admin, platform_admin)
    """
    auth_service = AuthService(db)
    user = await auth_service.register(user_data)
    return RegisterResponse(
        message="Registration successful. Please verify your email.", user=user
    )


@router.post(
    "/register/guardian",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new Guardian",
)
async def register_guardian(
    data: GuardianRegisterRequest, db: Session = Depends(get_db)
):
    """
    Register a new Guardian.
    This automatically creates a User and triggers the Guardian profile creation.
    """
    auth_service = AuthService(db)

    # Map the Guardian data to the standard RegisterRequest
    # This ensures AuthService and Event Handlers get what they expect
    user_data = RegisterRequest(
        email=data.email,
        password=data.password,
        first_name=data.first_name,
        last_name=data.last_name,
        user_type=UserType.GUARDIAN,  # Hardcoded here
        phone_number=data.phone_number,
        # We pass relationship_type here; your event handler uses getattr() to find it
        relationship_type=data.relationship_type,
    )

    user = await auth_service.register(user_data)

    return RegisterResponse(
        message="Guardian registration successful. Please verify your email.", user=user
    )


@router.post("/admin/create-user", response_model=RegisterResponse)
async def admin_create_user(
    user_data: RegisterRequest,
    _: None = Depends(require_roles("super_admin")),
    db: Session = Depends(get_db),
):
    """
    Create a new user account (Platform Admin only).

    This endpoint allows platform administrators to create user accounts
    with any user type. The created user will receive a verification email.

    - **email**: Valid email address
    - **password**: Min 8 characters with uppercase, lowercase, and number
    - **first_name**: User's first name
    - **last_name**: User's last name
    - **user_type**: Type of user (student, guardian, institution_admin, platform_admin)
    - **phone_number**: Optional phone number
    - **date_of_birth**: Optional date of birth
    - **username**: Optional username
    """

    try:
        auth_service = AuthService(db)
    except Exception as e:
        print(f"WARNING: Failed to configure email: {str(e)}")

    # Use the existing register method
    user = await auth_service.register(user_data, assign_default_role=False)

    return RegisterResponse(
        message=f"User created successfully. Verification email sent to {user.email}",
        user=user,
    )


@router.post(
    "/login", response_model=LoginResponse, summary="Login to get access token"
)
async def login(
    login_data: LoginRequest, request: Request, db: Session = Depends(get_db)
):
    """
    Authenticate user and get access tokens.

    - **email**: User's email address
    - **password**: User's password
    - **remember_me**: Keep user logged in for longer
    """
    # Get device info
    device_info = {
        "ip_address": request.client.host,
        "user_agent": request.headers.get("user-agent"),
    }

    auth_service = AuthService(db)
    response = await auth_service.login(login_data, device_info)

    return response


@router.post(
    "/admin/login",
    # Use the same response model
    response_model=LoginResponse,
    summary="Admin Login only",
)
async def admin_login(
    login_data: LoginRequest, request: Request, db: Session = Depends(get_db)
):
    """
    Authenticate administrative users only.
    Restricts access for 'guardian' and 'student' types.
    """
    device_info = {
        "ip_address": request.client.host,
        "user_agent": request.headers.get("user-agent"),
    }

    auth_service = AuthService(db)
    # Use a new service method specifically for admin login
    response = await auth_service.admin_login(login_data, device_info)

    return response


@router.post("/refresh", response_model=TokenResponse, summary="Refresh access token")
async def refresh_token(token_data: RefreshTokenRequest, db: Session = Depends(get_db)):
    """
    Get a new access token using refresh token.

    - **refresh_token**: Valid refresh token
    """
    auth_service = AuthService(db)
    tokens = await auth_service.refresh_access_token(token_data.refresh_token)

    return tokens


@router.post("/logout", response_model=MessageResponse, summary="Logout user")
async def logout(token_data: RefreshTokenRequest, db: Session = Depends(get_db)):
    """
    Logout user by revoking refresh token.

    - **refresh_token**: Refresh token to revoke
    """
    auth_service = AuthService(db)
    await auth_service.logout(token_data.refresh_token)

    return MessageResponse(message="Logout successful")


@router.post(
    "/logout-all", response_model=SuccessResponse, summary="Logout from all devices"
)
async def logout_all_devices(
    user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)
):
    """
    Logout user from all devices by revoking all refresh tokens.
    """
    auth_service = AuthService(db)
    count = await auth_service.logout_all_devices(user_id)

    return SuccessResponse(
        message=f"Logged out from {count} devices", data={"devices_count": count}
    )


@router.post(
    "/change-password", response_model=MessageResponse, summary="Change user password"
)
async def change_password(
    password_data: ChangePasswordRequest,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """
    Change current user's password.

    - **current_password**: Current password
    - **new_password**: New password (min 8 chars with requirements)
    """
    auth_service = AuthService(db)
    await auth_service.change_password(user_id, password_data)

    return MessageResponse(message="Password changed successfully")


@router.get("/me", response_model=UserResponse, summary="Get current user profile")
async def get_current_user(
    user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)
):
    """
    Get current authenticated user's profile.
    """
    from src.domains.auth.repositories.user_repository import UserRepository
    from src.core.exceptions import ResourceNotFoundException

    user_repo = UserRepository(db)
    user = user_repo.get_by_id(user_id)
    if not user:
        raise ResourceNotFoundException("User", user_id)

    return UserResponse.model_validate(user)


@router.patch(
    "/account/{user_id}",
    response_model=UserResponse,
    summary="Update user",
)
async def update_account(
    user_id: UUID,
    user_data: UserUpdate,
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
    """
    Update user details.

    - **first_name**: Updated first name
    - **last_name**: Updated last name
    - **middle_name**: Updated middle name
    - **phone_number**: Updated phone number
    - **date_of_birth**: Updated date of birth
    - **profile_picture_url**: Profile picture URL
    - **bio**: User bio
    - **language**: Preferred language
    - **timezone**: User's timezone
    """
    service = UserService(db)
    user = await service.update_user(user_id, user_data)
    return user


@router.post(
    "/forgot-password", response_model=MessageResponse, summary="Request password reset"
)
async def forgot_password(
    request_data: ForgotPasswordRequest, db: Session = Depends(get_db)
):
    """
    Request password reset link via email.
    """

    email_service = EmailService(db)
    user = db.query(User).filter(User.email == request_data.email).first()
    if user:
        reset_token = email_service.generate_token()
        token_expires = datetime.utcnow() + timedelta(
            minutes=settings.RESET_TOKEN_EXPIRE_MINUTES
        )
        user.password_reset_token = reset_token
        user.password_reset_token_expires = token_expires
        db.commit()
        try:
            client_type = determine_client_type(user)
            await email_service.send_email(
                to_email=user.email,
                subject="Password Reset Request",
                html_content=email_service.send_password_reset_email(
                    db=db, token=reset_token, client_type=client_type
                ),
            )
        except Exception as e:
            print(f"Failed to send email: {str(e)}")

    return MessageResponse(
        message="If the email exists, a password reset link has been sent"
    )


@router.post(
    "/reset-password",
    response_model=MessageResponse,
    summary="Reset password with token",
)
async def reset_password(
    reset_data: ResetPasswordRequest, db: Session = Depends(get_db)
):
    """
    Reset password using reset token.
    """
    user = (
        db.query(User)
        .filter(
            User.password_reset_token == reset_data.token,
            User.password_reset_token_expires > datetime.utcnow(),
        )
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    # Update password
    user.password_hash = hash_password(reset_data.new_password)
    user.password_reset_token = None
    user.password_reset_token_expires = None
    db.commit()

    return MessageResponse(message="Password reset successful")


@router.post(
    "/verify-email", response_model=MessageResponse, summary="Verify email address"
)
async def verify_email(verify_data: VerifyEmailRequest, db: Session = Depends(get_db)):
    """
    Verify user's email address.
    """
    user = (
        db.query(User)
        .filter(
            User.email_verification_token == verify_data.token,
            User.email_verification_token_expires > datetime.utcnow(),
        )
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token",
        )

    user.is_email_verified = True
    user.email_verified_at = datetime.now(timezone.utc)
    user.email_verification_token = None
    user.email_verification_token_expires = None
    db.commit()

    return MessageResponse(message="Email verified successfully")


@router.post(
    "/resend-verification",
    response_model=MessageResponse,
    summary="Resend verification email",
)
async def resend_verification(
    user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)
):
    """
    Resend email verification link.
    """
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    if user.is_email_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already verified"
        )

    email_service = EmailService(db)

    verify_token = email_service.generate_token()
    token_expires = datetime.utcnow() + timedelta(
        minutes=settings.VERIFY_TOKEN_EXPIRE_MINUTES
    )

    # Save token to database
    user.email_verification_token = verify_token
    user.email_verification_token_expires = token_expires
    db.commit()

    # Send email
    try:
        client_type = determine_client_type(user)

        await email_service.send_email(
            to_email=user.email,
            subject="Email Verification",
            html_content=email_service.send_verification_email(
                db=db, token=verify_token, client_type=client_type
            ),
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send verification email",
        )

    return MessageResponse(message="Verification email sent")
