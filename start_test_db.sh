#!/bin/bash
# Start the test database for running tests

set -e

echo "=========================================="
echo "Starting Test Database"
echo "=========================================="
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running!"
    echo ""
    echo "Please:"
    echo "  1. Open Docker Desktop"
    echo "  2. Wait for it to fully start"
    echo "  3. Run this script again"
    echo ""
    exit 1
fi

echo "✓ Docker is running"
echo ""

# Navigate to project directory
cd "$(dirname "$0")"

# Start the test database
echo "Starting test database container..."
docker-compose up -d db_test

# Wait for database to be ready
echo ""
echo "Waiting for database to be ready..."
sleep 3

# Check if database is healthy
max_attempts=30
attempt=0
while [ $attempt -lt $max_attempts ]; do
    if docker-compose exec -T db_test pg_isready -U postgres > /dev/null 2>&1; then
        echo "✓ Database is ready!"
        echo ""
        echo "You can now run tests with:"
        echo "  ./run_tests.sh"
        echo ""
        exit 0
    fi
    attempt=$((attempt + 1))
    echo "  Waiting... ($attempt/$max_attempts)"
    sleep 1
done

echo "⚠ Database might still be starting. You can check status with:"
echo "  docker-compose ps db_test"
echo ""
echo "Or try running tests anyway:"
echo "  ./run_tests.sh"

