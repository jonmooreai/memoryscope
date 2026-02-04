#!/bin/bash
# Check if test database is available and provide setup instructions

echo "Checking test database connection..."

# Try to connect to the test database
python3 << EOF
import os
from sqlalchemy import create_engine, text
from app.config import settings

test_db_url = settings.database_url_test or settings.database_url.replace(
    "/scoped_memory", "/scoped_memory_test"
)
# Replace Docker hostname with localhost
test_db_url = test_db_url.replace("db:", "localhost:").replace("db_test:", "localhost:")

try:
    engine = create_engine(test_db_url)
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    print("✓ Database connection successful!")
    print(f"  Using: {test_db_url}")
    exit(0)
except Exception as e:
    print("✗ Database connection failed!")
    print(f"  Error: {e}")
    print(f"  Attempted URL: {test_db_url}")
    print("")
    print("To fix this:")
    print("  1. Start Docker: docker-compose up -d db_test")
    print("  2. Or update DATABASE_URL_TEST in .env to point to a local PostgreSQL")
    print("     Example: postgresql+psycopg://postgres:postgres@localhost:5432/scoped_memory_test")
    exit(1)
EOF

