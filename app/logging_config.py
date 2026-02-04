"""
Structured logging configuration with request ID tracking.

This module provides centralized logging configuration following DRY principles.
All logging uses structured JSON format for production and human-readable format for development.
"""

import json
import logging
import sys
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from app.config import settings


class StructuredFormatter(logging.Formatter):
    """
    Structured JSON formatter for production logging.
    Includes request ID, timestamp, and all log fields in JSON format.
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add request ID if available
        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id
        
        # Add user_id if available
        if hasattr(record, "user_id"):
            log_data["user_id"] = record.user_id
        
        # Add app_id if available
        if hasattr(record, "app_id"):
            log_data["app_id"] = str(record.app_id)
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # Add any extra fields
        for key, value in record.__dict__.items():
            if key not in [
                "name", "levelno", "pathname", "filename", "module",
                "lineno", "funcName", "created", "msecs", "relativeCreated",
                "thread", "threadName", "processName", "process", "message",
                "exc_info", "exc_text", "stack_info", "request_id", "user_id", "app_id"
            ]:
                log_data[key] = value
        
        return json.dumps(log_data)


class HumanReadableFormatter(logging.Formatter):
    """
    Human-readable formatter for development.
    Includes request ID and all relevant information.
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as human-readable string."""
        parts = [
            f"[{record.levelname:8s}]",
            f"{record.module}:{record.lineno}",
        ]
        
        if hasattr(record, "request_id"):
            parts.append(f"req:{record.request_id[:8]}")
        
        if hasattr(record, "user_id"):
            parts.append(f"user:{record.user_id[:8]}")
        
        if hasattr(record, "app_id"):
            parts.append(f"app:{str(record.app_id)[:8]}")
        
        parts.append(record.getMessage())
        
        if record.exc_info:
            parts.append(f"\n{self.formatException(record.exc_info)}")
        
        return " | ".join(parts)


def setup_logging(use_json: Optional[bool] = None) -> None:
    """
    Set up application logging.
    
    Args:
        use_json: If True, use JSON formatting. If None, auto-detect based on environment.
    """
    # Determine format based on environment
    if use_json is None:
        # Use JSON in production, human-readable in development
        use_json = settings.log_level.upper() == "PRODUCTION" or settings.log_level.upper() == "JSON"
    
    # Create formatter
    if use_json:
        formatter = StructuredFormatter()
    else:
        formatter = HumanReadableFormatter()
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))
    
    # Remove existing handlers
    root_logger.handlers.clear()
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # Set levels for third-party loggers
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the given name.
    
    Args:
        name: Logger name (typically __name__)
    
    Returns:
        Logger instance
    """
    return logging.getLogger(name)


# Initialize logging on module import
setup_logging()

