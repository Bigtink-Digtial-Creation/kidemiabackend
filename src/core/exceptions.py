from typing import Optional, Any, Dict
from fastapi import HTTPException, status


class BaseAPIException(HTTPException):
    """Base exception for all API errors"""

    def __init__(
        self,
        status_code: int,
        detail: str,
        headers: Optional[Dict[str, str]] = None,
        error_code: Optional[str] = None,
    ):
        super().__init__(status_code=status_code, detail=detail, headers=headers)
        self.error_code = error_code


class AuthenticationException(BaseAPIException):
    """Base authentication exception"""

    def __init__(self, detail: str = "Authentication failed"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
            error_code="AUTH_ERROR",
        )


class InvalidCredentialsException(AuthenticationException):
    """Invalid username or password"""

    def __init__(self):
        super().__init__(detail="Invalid email or password")
        self.error_code = "INVALID_CREDENTIALS"


class TokenExpiredException(AuthenticationException):
    """Token has expired"""

    def __init__(self):
        super().__init__(detail="Token has expired")
        self.error_code = "TOKEN_EXPIRED"


class InvalidTokenException(AuthenticationException):
    """Invalid token"""

    def __init__(self):
        super().__init__(detail="Invalid token")
        self.error_code = "INVALID_TOKEN"


class AuthorizationException(BaseAPIException):
    """Base authorization exception"""

    def __init__(self, detail: str = "Access denied"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
            error_code="AUTHORIZATION_ERROR",
        )


class InsufficientPermissionsException(AuthorizationException):
    """User doesn't have required permissions"""

    def __init__(self, required_permission: Optional[str] = None):
        detail = "Insufficient permissions"
        if required_permission:
            detail = f"Required permission: {required_permission}"
        super().__init__(detail=detail)
        self.error_code = "INSUFFICIENT_PERMISSIONS"


class AccountDisabledException(AuthorizationException):
    """User account is disabled"""

    def __init__(self):
        super().__init__(detail="Your account has been disabled or deleted")
        self.error_code = "ACCOUNT_DISABLED"


class ResourceNotFoundException(BaseAPIException):
    """Resource not found"""

    def __init__(self, resource: str = "Resource", resource_id: Any = None):
        detail = f"{resource} not found"
        if resource_id:
            detail = f"{resource} with ID '{resource_id}' not found"
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail,
            error_code="RESOURCE_NOT_FOUND",
        )


class ResourceAlreadyExistsException(BaseAPIException):
    """Resource already exists"""

    def __init__(self, resource: str = "Resource", identifier: Optional[str] = None):
        detail = f"{resource} already exists"
        if identifier:
            detail = f"{resource} with {identifier} already exists"
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail,
            error_code="RESOURCE_ALREADY_EXISTS",
        )


class ResourceDeletedException(BaseAPIException):
    """Resource has been deleted"""

    def __init__(self, resource: str = "Resource"):
        super().__init__(
            status_code=status.HTTP_410_GONE,
            detail=f"{resource} has been deleted",
            error_code="RESOURCE_DELETED",
        )


class ValidationException(BaseAPIException):
    """Validation error"""

    def __init__(self, detail: str = "Validation error", field: Optional[str] = None):
        if field:
            detail = f"Validation error on field '{field}': {detail}"
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=detail,
            error_code="VALIDATION_ERROR",
        )


class InvalidInputException(ValidationException):
    """Invalid input provided"""

    def __init__(self, field: str, reason: str):
        super().__init__(detail=reason, field=field)
        self.error_code = "INVALID_INPUT"


class BusinessLogicException(BaseAPIException):
    """Base business logic exception"""

    def __init__(self, detail: str, status_code: int = status.HTTP_400_BAD_REQUEST):
        super().__init__(
            status_code=status_code, detail=detail, error_code="BUSINESS_LOGIC_ERROR"
        )


class ExamNotAvailableException(BusinessLogicException):
    """Exam is not available for taking"""

    def __init__(self, reason: str = "Exam is not available"):
        super().__init__(detail=reason)
        self.error_code = "EXAM_NOT_AVAILABLE"


class AttemptLimitExceededException(BusinessLogicException):
    """User has exceeded maximum attempts"""

    def __init__(self, max_attempts: int):
        super().__init__(detail=f"Maximum attempts ({max_attempts}) exceeded")
        self.error_code = "ATTEMPT_LIMIT_EXCEEDED"


class PaymentRequiredException(BusinessLogicException):
    """Payment required to access resource"""

    def __init__(self, resource: str = "this resource"):
        super().__init__(
            detail=f"Payment required to access {resource}",
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
        )
        self.error_code = "PAYMENT_REQUIRED"


class EnrollmentRequiredException(BusinessLogicException):
    """User must be enrolled to access resource"""

    def __init__(self):
        super().__init__(detail="You must be enrolled to access this resource")
        self.error_code = "ENROLLMENT_REQUIRED"


class ProctoringException(BusinessLogicException):
    """Base proctoring exception"""

    def __init__(self, detail: str):
        super().__init__(detail=detail)
        self.error_code = "PROCTORING_ERROR"


class ProctoringViolationException(ProctoringException):
    """Proctoring violation detected"""

    def __init__(self, violation_type: str):
        super().__init__(detail=f"Proctoring violation detected: {violation_type}")
        self.error_code = "PROCTORING_VIOLATION"


class SessionTerminatedException(ProctoringException):
    """Exam session has been terminated"""

    def __init__(self, reason: str):
        super().__init__(detail=f"Session terminated: {reason}")
        self.error_code = "SESSION_TERMINATED"


class SystemException(BaseAPIException):
    """Base system exception"""

    def __init__(self, detail: str = "System error occurred"):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail,
            error_code="SYSTEM_ERROR",
        )


class DatabaseException(SystemException):
    """Database operation failed"""

    def __init__(self, detail: str = "Database operation failed"):
        super().__init__(detail=detail)
        self.error_code = "DATABASE_ERROR"


class ExternalServiceException(SystemException):
    """External service call failed"""

    def __init__(self, service: str, detail: str = "Service unavailable"):
        super().__init__(detail=f"{service}: {detail}")
        self.error_code = "EXTERNAL_SERVICE_ERROR"


class RateLimitException(BaseAPIException):
    """Rate limit exceeded"""

    def __init__(self, retry_after: Optional[int] = None):
        detail = "Rate limit exceeded"
        headers = {}
        if retry_after:
            detail = f"Rate limit exceeded. Try again in {retry_after} seconds"
            headers["Retry-After"] = str(retry_after)

        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=detail,
            headers=headers,
            error_code="RATE_LIMIT_EXCEEDED",
        )
