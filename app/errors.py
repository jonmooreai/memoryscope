"""
Standardized error handling and response formatting.

This module provides centralized error handling following DRY principles.
All errors follow a consistent format with request IDs and helpful messages.
"""

import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.logging_config import get_logger
from app.monitoring import capture_exception

logger = get_logger(__name__)


class APIError(Exception):
    """Base exception for API errors."""
    
    def __init__(
        self,
        message: str,
        code: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class ValidationError(APIError):
    """Validation error."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            status_code=status.HTTP_400_BAD_REQUEST,
            details=details,
        )


class AuthenticationError(APIError):
    """Authentication error."""
    
    def __init__(self, message: str = "Authentication required"):
        super().__init__(
            message=message,
            code="AUTHENTICATION_ERROR",
            status_code=status.HTTP_401_UNAUTHORIZED,
        )


class AuthorizationError(APIError):
    """Authorization error."""
    
    def __init__(self, message: str = "Insufficient permissions"):
        super().__init__(
            message=message,
            code="AUTHORIZATION_ERROR",
            status_code=status.HTTP_403_FORBIDDEN,
        )


class NotFoundError(APIError):
    """Resource not found error."""
    
    def __init__(self, resource: str = "Resource"):
        super().__init__(
            message=f"{resource} not found",
            code="NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND,
        )


class RateLimitError(APIError):
    """Rate limit exceeded error."""
    
    def __init__(self, message: str = "Rate limit exceeded", retry_after: Optional[int] = None):
        details = {}
        if retry_after:
            details["retry_after"] = retry_after
        
        super().__init__(
            message=message,
            code="RATE_LIMIT_EXCEEDED",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            details=details,
        )


def format_error_response(
    request: Request,
    error: Exception,
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
    code: Optional[str] = None,
    message: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
) -> JSONResponse:
    """
    Format error response in standard format.
    
    Args:
        request: FastAPI request object
        error: Exception that occurred
        status_code: HTTP status code
        code: Error code
        message: Error message
        details: Additional error details
    
    Returns:
        JSONResponse with formatted error
    """
    # Get request ID
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    
    # Determine error code and message
    if isinstance(error, APIError):
        error_code = error.code
        error_message = error.message
        error_status = error.status_code
        error_details = error.details
    else:
        error_code = code or "INTERNAL_SERVER_ERROR"
        error_message = message or "An unexpected error occurred"
        error_status = status_code
        error_details = details or {}
    
    # Log error
    logger.error(
        f"Error: {error_message}",
        exc_info=error if not isinstance(error, APIError) else None,
        extra={
            "request_id": request_id,
            "error_code": error_code,
            "status_code": error_status,
        }
    )
    
    # Capture in Sentry for server errors
    if error_status >= 500:
        capture_exception(
            error if not isinstance(error, APIError) else Exception(error_message),
            context={
                "request_id": request_id,
                "error_code": error_code,
                "status_code": error_status,
                "path": str(request.url.path),
                "method": request.method,
            }
        )
    
    # Build error response
    error_response = {
        "error": {
            "code": error_code,
            "message": error_message,
            "request_id": request_id,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
    }
    
    # Add details if present
    if error_details:
        error_response["error"]["details"] = error_details
    
    # Add recovery hints for common errors
    if error_code == "VALIDATION_ERROR":
        error_response["error"]["hint"] = "Check the request format and required fields"
    elif error_code == "AUTHENTICATION_ERROR":
        error_response["error"]["hint"] = "Verify your API key or authentication token"
    elif error_code == "RATE_LIMIT_EXCEEDED":
        if "retry_after" in error_details:
            error_response["error"]["hint"] = f"Retry after {error_details['retry_after']} seconds"
    
    return JSONResponse(
        status_code=error_status,
        content=error_response,
        headers={"X-Request-ID": request_id},
    )


async def api_error_handler(request: Request, exc: APIError) -> JSONResponse:
    """Handle APIError exceptions."""
    return format_error_response(request, exc)


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Handle HTTPException exceptions."""
    return format_error_response(
        request,
        exc,
        status_code=exc.status_code,
        code="HTTP_ERROR",
        message=exc.detail,
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle validation errors."""
    errors = []
    for error in exc.errors():
        errors.append({
            "field": ".".join(str(loc) for loc in error["loc"]),
            "message": error["msg"],
            "type": error["type"],
        })
    
    return format_error_response(
        request,
        exc,
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        code="VALIDATION_ERROR",
        message="Request validation failed",
        details={"fields": errors},
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle all other exceptions."""
    return format_error_response(
        request,
        exc,
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        code="INTERNAL_SERVER_ERROR",
        message="An unexpected error occurred",
    )

