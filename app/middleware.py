"""
Request middleware for tracking and logging.

This module provides middleware for:
- Request ID generation and tracking
- Request/response logging
- Performance metrics
"""

import time
import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.logging_config import get_logger

logger = get_logger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware to generate and track request IDs.
    Adds X-Request-ID header to all responses.
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate or get request ID
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        
        # Store in request state
        request.state.request_id = request_id
        
        # Add to logger context
        logger.info(
            f"{request.method} {request.url.path}",
            extra={"request_id": request_id}
        )
        
        # Process request
        start_time = time.time()
        try:
            response = await call_next(request)
        except Exception as e:
            # Log error with request ID
            logger.error(
                f"Request failed: {str(e)}",
                exc_info=True,
                extra={"request_id": request_id}
            )
            raise
        finally:
            # Calculate duration
            duration = time.time() - start_time
            
            # Log performance (only if response exists)
            if 'response' in locals():
                logger.info(
                    f"{request.method} {request.url.path} - {response.status_code} - {duration:.3f}s",
                    extra={
                        "request_id": request_id,
                        "status_code": response.status_code,
                        "duration_ms": duration * 1000,
                    }
                )
                # Add request ID to response header
                response.headers["X-Request-ID"] = request_id
        
        return response


class PerformanceMiddleware(BaseHTTPMiddleware):
    """
    Middleware to track request performance metrics.
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        
        response = await call_next(request)
        
        duration = time.time() - start_time
        
        # Log slow requests
        if duration > 1.0:  # Log requests taking more than 1 second
            request_id = getattr(request.state, "request_id", "unknown")
            logger.warning(
                f"Slow request: {request.method} {request.url.path} took {duration:.3f}s",
                extra={
                    "request_id": request_id,
                    "duration_ms": duration * 1000,
                    "slow_request": True,
                }
            )
        
        # Add performance header
        response.headers["X-Response-Time"] = f"{duration:.3f}"
        
        return response

