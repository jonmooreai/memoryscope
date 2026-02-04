"""
Input sanitization and validation utilities.

This module provides centralized sanitization functions following DRY principles.
All user input should be sanitized before use to prevent security issues.
"""

import re
import html
from typing import Optional, Union, Dict, Any, List
from urllib.parse import quote, unquote


# Maximum lengths for various fields
MAX_USER_ID_LENGTH = 255
MAX_SCOPE_LENGTH = 50
MAX_DOMAIN_LENGTH = 500
MAX_PURPOSE_LENGTH = 1000
MAX_SOURCE_LENGTH = 50


def sanitize_user_id(user_id: str) -> str:
    """
    Sanitize user ID to prevent injection attacks.
    
    Args:
        user_id: User identifier
    
    Returns:
        Sanitized user ID
    
    Raises:
        ValueError: If user_id is invalid
    """
    if not user_id:
        raise ValueError("user_id cannot be empty")
    
    # Remove whitespace
    user_id = user_id.strip()
    
    # Check length
    if len(user_id) > MAX_USER_ID_LENGTH:
        raise ValueError(f"user_id exceeds maximum length of {MAX_USER_ID_LENGTH}")
    
    # Allow alphanumeric, underscore, hyphen, dot, @ (for emails)
    # This is permissive but safe - adjust based on your user ID format
    if not re.match(r'^[a-zA-Z0-9_\-\.@]+$', user_id):
        raise ValueError("user_id contains invalid characters")
    
    return user_id


def sanitize_scope(scope: str) -> str:
    """
    Sanitize scope value.
    
    Args:
        scope: Scope string
    
    Returns:
        Sanitized scope
    
    Raises:
        ValueError: If scope is invalid
    """
    if not scope:
        raise ValueError("scope cannot be empty")
    
    scope = scope.strip().lower()
    
    if len(scope) > MAX_SCOPE_LENGTH:
        raise ValueError(f"scope exceeds maximum length of {MAX_SCOPE_LENGTH}")
    
    # Scope should only contain lowercase letters and underscores
    if not re.match(r'^[a-z_]+$', scope):
        raise ValueError("scope contains invalid characters")
    
    return scope


def sanitize_domain(domain: Optional[str]) -> Optional[str]:
    """
    Sanitize domain value.
    
    Args:
        domain: Domain string (can be None)
    
    Returns:
        Sanitized domain or None
    
    Raises:
        ValueError: If domain is invalid
    """
    if domain is None:
        return None
    
    domain = domain.strip()
    
    if not domain:
        return None
    
    if len(domain) > MAX_DOMAIN_LENGTH:
        raise ValueError(f"domain exceeds maximum length of {MAX_DOMAIN_LENGTH}")
    
    # Domain can contain alphanumeric, spaces, hyphens, underscores, dots, slashes
    # This is permissive for domain values like "food/preferences" or "work.settings"
    if not re.match(r'^[a-zA-Z0-9_\-\.\/\s]+$', domain):
        raise ValueError("domain contains invalid characters")
    
    return domain


def sanitize_purpose(purpose: str) -> str:
    """
    Sanitize purpose string.
    
    Args:
        purpose: Purpose description
    
    Returns:
        Sanitized purpose
    
    Raises:
        ValueError: If purpose is invalid
    """
    if not purpose:
        raise ValueError("purpose cannot be empty")
    
    purpose = purpose.strip()
    
    if len(purpose) > MAX_PURPOSE_LENGTH:
        raise ValueError(f"purpose exceeds maximum length of {MAX_PURPOSE_LENGTH}")
    
    # Purpose can contain letters, numbers, spaces, and common punctuation
    # Remove any HTML/script tags
    purpose = html.escape(purpose)
    
    return purpose


def sanitize_source(source: str) -> str:
    """
    Sanitize source value.
    
    Args:
        source: Source string
    
    Returns:
        Sanitized source
    
    Raises:
        ValueError: If source is invalid
    """
    if not source:
        raise ValueError("source cannot be empty")
    
    source = source.strip().lower()
    
    if len(source) > MAX_SOURCE_LENGTH:
        raise ValueError(f"source exceeds maximum length of {MAX_SOURCE_LENGTH}")
    
    # Source should only contain lowercase letters and underscores
    if not re.match(r'^[a-z_]+$', source):
        raise ValueError("source contains invalid characters")
    
    return source


def sanitize_string(value: str, max_length: Optional[int] = None, allow_html: bool = False) -> str:
    """
    General string sanitization.
    
    Args:
        value: String to sanitize
        max_length: Maximum length (optional)
        allow_html: Whether to allow HTML (default: False - escapes HTML)
    
    Returns:
        Sanitized string
    
    Raises:
        ValueError: If value is invalid
    """
    if not isinstance(value, str):
        raise ValueError("value must be a string")
    
    value = value.strip()
    
    if max_length and len(value) > max_length:
        raise ValueError(f"value exceeds maximum length of {max_length}")
    
    # Escape HTML unless explicitly allowed
    if not allow_html:
        value = html.escape(value)
    
    return value


def validate_no_sql_injection(value: str) -> bool:
    """
    Basic check for SQL injection patterns.
    
    Note: This is a basic check. SQLAlchemy parameterized queries
    provide the real protection, but this adds an extra layer.
    
    Args:
        value: String to check
    
    Returns:
        True if safe, False if suspicious
    """
    # Common SQL injection patterns
    sql_patterns = [
        r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|EXECUTE)\b)",
        r"(--|#|\/\*|\*\/)",  # SQL comments
        r"(\b(UNION|OR|AND)\s+\d+)",  # UNION/OR/AND with numbers
        r"('|;|\\)",  # Quote and semicolon patterns
    ]
    
    value_upper = value.upper()
    for pattern in sql_patterns:
        if re.search(pattern, value_upper, re.IGNORECASE):
            return False
    
    return True


def sanitize_json_value(value: Union[Dict[str, Any], List[Any]]) -> Union[Dict[str, Any], List[Any]]:
    """
    Sanitize JSON values to prevent injection.
    
    This recursively sanitizes string values in JSON structures.
    
    Args:
        value: JSON value (dict or list)
    
    Returns:
        Sanitized JSON value
    """
    if isinstance(value, dict):
        return {k: sanitize_json_value(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [sanitize_json_value(item) for item in value]
    elif isinstance(value, str):
        # Escape HTML in string values
        return html.escape(value)
    else:
        # Numbers, booleans, None are safe
        return value

