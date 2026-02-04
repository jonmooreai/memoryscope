"""
Rate limiting utilities for API endpoints.
"""
import logging
from typing import Optional
from functools import wraps

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request, HTTPException, status

logger = logging.getLogger(__name__)

# Create limiter instance
# Use in-memory storage by default (can be configured to use Redis for distributed systems)
limiter = Limiter(
    key_func=get_remote_address,  # Default key function (can be overridden per endpoint)
    default_limits=["1000/hour"],  # Default limit if not specified
    storage_uri="memory://",  # In-memory storage (use "redis://localhost:6379" for production)
)


def get_api_key_identifier(request: Request) -> str:
    """
    Get rate limit key based on API key from request.
    
    This function extracts the API key from the X-API-Key header and uses it
    as the identifier for rate limiting. This ensures rate limits are per API key.
    
    Args:
        request: FastAPI request object
        
    Returns:
        API key string, or IP address if API key not found
    """
    api_key = request.headers.get("X-API-Key")
    if api_key:
        # Use API key as identifier (rate limit per API key)
        return f"api_key:{api_key}"
    # Fallback to IP address if no API key
    return get_remote_address(request)


def get_app_id_identifier(request: Request) -> str:
    """
    Get rate limit key based on app ID from request state.
    
    This function uses the app.id from request.state (set by get_app_from_api_key)
    as the identifier for rate limiting. This is more efficient than using the API key.
    
    Args:
        request: FastAPI request object
        
    Returns:
        App ID string, or IP address if app not found
    """
    # Check if app was set by get_app_from_api_key dependency
    if hasattr(request.state, "app") and hasattr(request.state.app, "id"):
        return f"app_id:{request.state.app.id}"
    
    # Fallback to API key or IP
    return get_api_key_identifier(request)


# Custom exception handler for rate limit errors
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    """
    Custom handler for rate limit exceeded errors.
    
    Returns a proper HTTP 429 response with retry-after header.
    """
    from fastapi.responses import JSONResponse
    
    response = JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={
            "error": "rate_limit_exceeded",
            "message": "Rate limit exceeded. Please try again later.",
            "retry_after": exc.retry_after,
        },
        headers={"Retry-After": str(exc.retry_after)} if exc.retry_after else {},
    )
    return response


# Rate limit decorator for endpoints that use API key authentication
def rate_limit_by_api_key(limit: str):
    """
    Decorator to apply rate limiting based on API key.
    
    Usage:
        @app.post("/memory")
        @rate_limit_by_api_key("1000/hour")
        def create_memory(...):
            ...
    
    Args:
        limit: Rate limit string (e.g., "1000/hour", "100/minute", "10/second")
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract request from kwargs or args
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            if not request:
                request = kwargs.get("request")
            
            if request:
                # Apply rate limit using API key identifier
                limiter.limit(limit, key_func=get_api_key_identifier)(func)(*args, **kwargs)
            
            return await func(*args, **kwargs) if hasattr(func, "__call__") else func(*args, **kwargs)
        return wrapper
    return decorator

