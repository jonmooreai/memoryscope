import pytest
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
import uuid
from datetime import datetime

from app.database import Base, get_db
from app.main import app, _get_app
from app.models import App
from app.utils import hash_api_key
from app.config import settings
import subprocess
import os


@pytest.fixture(scope="session")
def test_db_engine():
    """Create test database engine and run migrations."""
    # Use test database URL if available, otherwise fall back to main DB with _test suffix
    test_db_url = settings.database_url_test or settings.database_url.replace(
        "/scoped_memory", "/scoped_memory_test"
    )
    # Replace Docker hostname with localhost for local testing
    # Only change port if we're actually using Docker hostnames (db: or db_test:)
    # If already using localhost, keep the port as-is
    if "db:" in test_db_url or "db_test:" in test_db_url:
        # Docker container: db_test maps to port 5433 on localhost, db maps to 5432
        if "db_test:" in test_db_url:
            # db_test container uses port 5433 when accessed from localhost
            test_db_url = test_db_url.replace("db_test:", "localhost:")
            test_db_url = test_db_url.replace("localhost:5432/scoped_memory_test", "localhost:5433/scoped_memory_test")
        else:
            # db container uses port 5432
            test_db_url = test_db_url.replace("db:", "localhost:")
    # If already using localhost, don't change anything - use it as-is
    
    engine = create_engine(test_db_url)
    
    # Drop all tables including alembic_version
    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA IF EXISTS public CASCADE;"))
        conn.execute(text("CREATE SCHEMA public;"))
    
    # Grant permissions in separate transactions to avoid transaction rollback issues
    # These are not critical for tests to work
    try:
        with engine.begin() as conn:
            conn.execute(text("GRANT ALL ON SCHEMA public TO postgres;"))
    except Exception:
        pass  # postgres role might not exist (e.g., Homebrew PostgreSQL)
    
    try:
        with engine.begin() as conn:
            conn.execute(text("GRANT ALL ON SCHEMA public TO public;"))
    except Exception:
        pass  # May fail in some PostgreSQL configurations
    
    # Create tables directly using SQLAlchemy (simpler than alembic for tests)
    # This avoids issues with local alembic directory shadowing installed package
    from app.database import Base
    Base.metadata.create_all(bind=engine)
    
    yield engine
    
    # Cleanup: drop all tables
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture(scope="function")
def test_db(test_db_engine):
    """Create a test database session for each test function."""
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_db_engine)
    
    # Clean all tables before each test using DELETE (simpler than TRUNCATE)
    with test_db_engine.begin() as conn:
        # Delete in reverse dependency order
        for table in reversed(Base.metadata.sorted_tables):
            try:
                conn.execute(text(f"DELETE FROM {table.name};"))
            except Exception:
                # Table might not exist, ignore
                pass
    
    def override_get_db():
        try:
            db = TestingSessionLocal()
            yield db
        finally:
            db.close()
    
    app.dependency_overrides[get_db] = override_get_db
    yield TestingSessionLocal
    app.dependency_overrides.clear()


@pytest.fixture
def test_app(test_db):
    """Create a test app with API key."""
    db = test_db()
    api_key = "test-api-key-123"
    api_key_hash = hash_api_key(api_key)
    app_obj = App(
        id=uuid.uuid4(),
        name="Test App",
        api_key_hash=api_key_hash,
        user_id="test-user-id",  # Required field
        created_at=datetime.utcnow(),
    )
    db.add(app_obj)
    db.commit()
    db.refresh(app_obj)
    db.close()
    return app_obj, api_key


@pytest.fixture
def client(test_db, test_app):
    """Create a test client. Override _get_app to use the test app (no API key auth)."""
    app_obj, _ = test_app
    app.dependency_overrides[_get_app] = lambda: app_obj
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(_get_app, None)


@pytest.fixture
def api_key(test_app):
    """Return the API key for the test app."""
    return test_app[1]


@pytest.fixture
def app_id(test_app):
    """Return the app ID for the test app."""
    return test_app[0].id
