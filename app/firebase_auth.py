"""
Firebase authentication utilities for token verification.
"""
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

try:
    import firebase_admin
    from firebase_admin import credentials, auth
    FIREBASE_AVAILABLE = True
except ImportError:
    FIREBASE_AVAILABLE = False
    firebase_admin = None
    auth = None
    logger.warning("firebase-admin not installed. Token verification will be disabled.")


# Global flag to track if Firebase is initialized
_firebase_initialized = False


def initialize_firebase_admin() -> None:
    """
    Initialize Firebase Admin SDK for authentication.
    
    This should be called once at application startup.
    Supports multiple initialization methods:
    1. Service account key file (FIREBASE_SERVICE_ACCOUNT_PATH)
    2. Service account JSON in environment variable (FIREBASE_SERVICE_ACCOUNT_JSON)
    3. Default credentials (for Google Cloud environments)
    """
    global _firebase_initialized
    
    if not FIREBASE_AVAILABLE:
        logger.warning("Firebase Admin SDK not available. Token verification disabled.")
        return
    
    # Check if already initialized
    if firebase_admin._apps:
        _firebase_initialized = True
        logger.info("Firebase Admin SDK already initialized")
        return
    
    # Option 1: Use service account key file
    service_account_path = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH")
    if service_account_path and os.path.exists(service_account_path):
        try:
            cred = credentials.Certificate(service_account_path)
            firebase_admin.initialize_app(cred)
            _firebase_initialized = True
            logger.info("Firebase Admin SDK initialized from service account file")
            return
        except Exception as e:
            logger.error(f"Failed to initialize Firebase from service account file: {e}")
            raise
    
    # Option 2: Use service account JSON from environment variable
    service_account_json = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")
    if service_account_json:
        try:
            import json
            cred = credentials.Certificate(json.loads(service_account_json))
            firebase_admin.initialize_app(cred)
            _firebase_initialized = True
            logger.info("Firebase Admin SDK initialized from environment variable")
            return
        except Exception as e:
            logger.error(f"Failed to initialize Firebase from JSON: {e}")
            raise
    
    # Option 3: Use default credentials (for Google Cloud environments)
    try:
        firebase_admin.initialize_app()
        _firebase_initialized = True
        logger.info("Firebase Admin SDK initialized with default credentials")
        return
    except Exception as e:
        logger.warning(
            f"Firebase Admin SDK initialization failed: {e}. "
            "Token verification will be disabled. Set FIREBASE_SERVICE_ACCOUNT_PATH or "
            "FIREBASE_SERVICE_ACCOUNT_JSON environment variable for production."
        )
        _firebase_initialized = False


def verify_id_token(token: str, check_revoked: bool = True) -> dict:
    """
    Verify a Firebase ID token and return the decoded token.
    
    Args:
        token: The Firebase ID token to verify
        check_revoked: Whether to check if the token has been revoked
        
    Returns:
        Decoded token dictionary containing user information
        
    Raises:
        ValueError: If token is invalid, expired, or revoked
        Exception: If Firebase is not initialized
    """
    if not FIREBASE_AVAILABLE:
        raise ValueError("Firebase Admin SDK not available")
    
    if not _firebase_initialized:
        raise ValueError("Firebase Admin SDK not initialized")
    
    try:
        decoded_token = auth.verify_id_token(token, check_revoked=check_revoked)
        return decoded_token
    except auth.InvalidIdTokenError as e:
        logger.warning(f"Invalid Firebase token: {e}")
        raise ValueError(f"Invalid token: {e}") from e
    except auth.ExpiredIdTokenError as e:
        logger.warning(f"Expired Firebase token: {e}")
        raise ValueError(f"Token expired: {e}") from e
    except auth.RevokedIdTokenError as e:
        logger.warning(f"Revoked Firebase token: {e}")
        raise ValueError(f"Token revoked: {e}") from e
    except Exception as e:
        logger.error(f"Error verifying Firebase token: {e}")
        raise ValueError(f"Token verification failed: {e}") from e


def is_firebase_initialized() -> bool:
    """Check if Firebase Admin SDK is initialized."""
    return _firebase_initialized and FIREBASE_AVAILABLE

