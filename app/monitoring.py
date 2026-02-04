"""
Monitoring and error tracking configuration.

This module provides centralized monitoring setup following DRY principles.
Integrates Sentry for error tracking when configured.
"""

import logging
from typing import Optional

from app.config import settings

logger = logging.getLogger(__name__)


def setup_sentry() -> Optional[object]:
    """
    Initialize Sentry for error tracking if DSN is configured.
    
    Returns:
        Sentry SDK instance or None if not configured
    """
    if not settings.sentry_dsn:
        logger.info("Sentry not configured (SENTRY_DSN not set)")
        return None
    
    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
        from sentry_sdk.integrations.logging import LoggingIntegration
        
        # Configure Sentry
        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            environment=settings.environment,
            integrations=[
                FastApiIntegration(),
                SqlalchemyIntegration(),
                LoggingIntegration(
                    level=logging.INFO,  # Capture info and above
                    event_level=logging.ERROR  # Send errors as events
                ),
            ],
            # Set traces_sample_rate to 1.0 to capture 100% of transactions
            # Adjust in production
            traces_sample_rate=0.1 if settings.environment == "production" else 1.0,
            # Set profiles_sample_rate to profile performance
            profiles_sample_rate=0.1 if settings.environment == "production" else 1.0,
            # Release tracking
            release=f"memory-scope-api@{settings.environment}",
            # Filter out health check endpoints
            ignore_errors=[
                KeyboardInterrupt,
                SystemExit,
            ],
        )
        
        logger.info(f"Sentry initialized for environment: {settings.environment}")
        return sentry_sdk
        
    except ImportError:
        logger.warning("sentry-sdk not installed. Install with: pip install sentry-sdk[fastapi]")
        return None
    except Exception as e:
        logger.error(f"Failed to initialize Sentry: {e}", exc_info=True)
        return None


def capture_exception(error: Exception, context: Optional[dict] = None) -> None:
    """
    Capture exception in Sentry if configured.
    
    Args:
        error: Exception to capture
        context: Additional context to include
    """
    try:
        import sentry_sdk
        
        if context:
            with sentry_sdk.push_scope() as scope:
                for key, value in context.items():
                    scope.set_extra(key, value)
                sentry_sdk.capture_exception(error)
        else:
            sentry_sdk.capture_exception(error)
    except ImportError:
        pass  # Sentry not installed
    except Exception:
        pass  # Don't fail if Sentry fails


def capture_message(message: str, level: str = "info", context: Optional[dict] = None) -> None:
    """
    Capture message in Sentry if configured.
    
    Args:
        message: Message to capture
        level: Log level (info, warning, error)
        context: Additional context to include
    """
    try:
        import sentry_sdk
        
        if context:
            with sentry_sdk.push_scope() as scope:
                for key, value in context.items():
                    scope.set_extra(key, value)
                sentry_sdk.capture_message(message, level=level)
        else:
            sentry_sdk.capture_message(message, level=level)
    except ImportError:
        pass  # Sentry not installed
    except Exception:
        pass  # Don't fail if Sentry fails

