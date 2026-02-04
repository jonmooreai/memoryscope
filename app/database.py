"""
Database configuration with optimized connection pooling and retry logic.

This module provides centralized database configuration following DRY principles.
Includes connection pooling, retry logic, and health checks.
"""

import time
import logging
from contextlib import contextmanager
from typing import TYPE_CHECKING
from sqlalchemy import create_engine, event, pool
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import OperationalError, DisconnectionError

from app.config import settings

if TYPE_CHECKING:
    from sqlalchemy.orm import Session
    from app.models import App

logger = logging.getLogger(__name__)

# Optimized connection pool configuration
engine = create_engine(
    settings.database_url,
    pool_size=15,  # Number of connections to maintain
    max_overflow=20,  # Maximum connections beyond pool_size
    pool_timeout=30,  # Seconds to wait for connection from pool
    pool_recycle=3600,  # Recycle connections after 1 hour
    pool_pre_ping=True,  # Verify connections before using
    echo=False,  # Set to True for SQL query logging
    connect_args={
        "connect_timeout": 10,  # Connection timeout in seconds
        "options": "-c statement_timeout=30000",  # Query timeout (30 seconds)
    }
)

# Add connection retry logic
@event.listens_for(engine, "connect")
def set_connection_timeout(dbapi_conn, connection_record):
    """Set connection-level timeouts."""
    with dbapi_conn.cursor() as cursor:
        cursor.execute("SET statement_timeout = '30s'")
        cursor.execute("SET idle_in_transaction_session_timeout = '60s'")


@event.listens_for(engine, "checkout")
def receive_checkout(dbapi_conn, connection_record, connection_proxy):
    """Handle connection checkout with retry logic."""
    from sqlalchemy import text
    retry_count = 0
    max_retries = 3
    
    while retry_count < max_retries:
        try:
            # Test connection
            with dbapi_conn.cursor() as cursor:
                cursor.execute("SELECT 1")
            break
        except (OperationalError, DisconnectionError) as e:
            retry_count += 1
            if retry_count >= max_retries:
                logger.error(f"Failed to get database connection after {max_retries} retries: {e}")
                raise
            time.sleep(0.1 * retry_count)  # Exponential backoff


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """
    Get database session with automatic cleanup.
    
    Yields:
        Database session
    """
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        db.rollback()
        logger.error(f"Database session error: {e}", exc_info=True)
        raise
    finally:
        db.close()


@contextmanager
def get_db_context():
    """
    Context manager for database sessions.
    Useful for operations that need explicit transaction control.
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def get_default_app(db: "Session") -> "App":
    """
    Return the single default app used for all requests (core API, no API keys).
    Creates the default app if it does not exist.
    """
    from app.models import App
    from app.utils import hash_api_key
    import uuid as uuid_mod
    default = db.query(App).filter(App.name == "default").first()
    if default is not None:
        return default
    # Create default app (no API key issued; hash is a placeholder)
    placeholder_secret = str(uuid_mod.uuid4())
    default = App(
        name="default",
        api_key_hash=hash_api_key(placeholder_secret),
        user_id="system",
    )
    db.add(default)
    db.commit()
    db.refresh(default)
    return default


def check_database_health() -> dict:
    """
    Check database health and connectivity.
    
    Returns:
        Dictionary with health status and metrics
    """
    try:
        from sqlalchemy import text
        start_time = time.time()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        response_time = (time.time() - start_time) * 1000  # Convert to ms
        
        pool_status = {
            "size": engine.pool.size(),
            "checked_in": engine.pool.checkedin(),
            "checked_out": engine.pool.checkedout(),
            "overflow": engine.pool.overflow(),
        }
        
        return {
            "status": "healthy",
            "response_time_ms": round(response_time, 2),
            "pool": pool_status,
        }
    except Exception as e:
        logger.error(f"Database health check failed: {e}", exc_info=True)
        return {
            "status": "unhealthy",
            "error": str(e),
        }

