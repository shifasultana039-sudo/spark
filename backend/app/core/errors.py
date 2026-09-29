"""
Domain exception hierarchy and standard HTTP error handlers for ReliefChain AI.
"""

from typing import Any, Dict, Optional
from fastapi import Request, status
from fastapi.responses import JSONResponse

class AppException(Exception):
    """Base application exception for ReliefChain AI."""
    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_code: str = "INTERNAL_ERROR",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details or {}

class NotFoundError(AppException):
    def __init__(self, message: str = "Resource not found", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="RESOURCE_NOT_FOUND",
            details=details
        )

class ValidationError(AppException):
    def __init__(self, message: str = "Validation failed", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="VALIDATION_FAILED",
            details=details
        )

class ResourceConflictError(AppException):
    def __init__(self, message: str = "Resource conflict detected", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_409_CONFLICT,
            error_code="RESOURCE_CONFLICT",
            details=details
        )

class UnauthorizedError(AppException):
    def __init__(self, message: str = "Authentication required", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code="UNAUTHORIZED",
            details=details
        )

class ForbiddenError(AppException):
    def __init__(self, message: str = "Access forbidden", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
            error_code="FORBIDDEN",
            details=details
        )

async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """Standardized JSON response for domain application exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": exc.error_code,
                "message": exc.message,
                "details": exc.details
            }
        }
    )

from fastapi.encoders import jsonable_encoder

async def validation_exception_handler(request: Request, exc: Any) -> JSONResponse:
    """Standardized JSON response for Pydantic/FastAPI validation exceptions."""
    raw_errors = exc.errors() if hasattr(exc, "errors") else [{"msg": str(exc)}]
    safe_details = jsonable_encoder(raw_errors)
    msg = raw_errors[0].get("msg", "Validation error") if raw_errors and isinstance(raw_errors[0], dict) else "Validation error"
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "error": {
                "code": "VALIDATION_FAILED",
                "message": f"Input validation failed: {msg}",
                "details": safe_details
            }
        }
    )


async def http_exception_handler(request: Request, exc: Any) -> JSONResponse:
    """Standardized JSON response for HTTPException."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": "HTTP_ERROR",
                "message": getattr(exc, "detail", str(exc)),
                "details": {}
            }
        }
    )

async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Fallback handler for unhandled server exceptions."""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": {
                "code": "SERVER_ERROR",
                "message": "An unexpected server error occurred.",
                "details": {"exception_type": type(exc).__name__, "description": str(exc)}
            }
        }
    )


