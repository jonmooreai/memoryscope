#!/bin/bash
# Setup script for local PostgreSQL test database (without Docker)

set -e

echo "=========================================="
echo "Local PostgreSQL Test Database Setup"
echo "=========================================="
echo ""

# Check if PostgreSQL is installed
if ! command -v psql &> /dev/null; then
    echo "❌ PostgreSQL (psql) not found!"
    echo ""
    echo "Please install PostgreSQL first:"
    echo ""
    echo "  macOS (Homebrew):"
    echo "    brew install postgresql@16"
    echo "    brew services start postgresql@16"
    echo ""
    echo "  macOS (Postgres.app):"
    echo "    Download from: https://postgresapp.com/"
    echo ""
    echo "  Linux:"
    echo "    sudo apt install postgresql postgresql-contrib"
    echo ""
    echo "  Windows:"
    echo "    Download from: https://www.postgresql.org/download/windows/"
    echo ""
    exit 1
fi

echo "✓ PostgreSQL found: $(psql --version)"
echo ""

# Check if PostgreSQL is running
if ! pg_isready -h localhost -p 5432 > /dev/null 2>&1; then
    echo "⚠ PostgreSQL is not running!"
    echo ""
    echo "Please start PostgreSQL:"
    echo "  macOS (Homebrew): brew services start postgresql@16"
    echo "  Linux: sudo systemctl start postgresql"
    echo "  Or start Postgres.app if using that"
    echo ""
    exit 1
fi

echo "✓ PostgreSQL is running"
echo ""

# Try to create database
echo "Creating test database 'scoped_memory_test'..."

# Try with default postgres user
if psql -U postgres -h localhost -c "CREATE DATABASE scoped_memory_test;" 2>/dev/null; then
    echo "✓ Database created successfully!"
elif psql -h localhost -c "CREATE DATABASE scoped_memory_test;" 2>/dev/null; then
    echo "✓ Database created successfully!"
else
    echo "⚠ Could not create database automatically"
    echo ""
    echo "Please create it manually:"
    echo "  psql -U postgres"
    echo "  CREATE DATABASE scoped_memory_test;"
    echo "  \\q"
    echo ""
    read -p "Press Enter after creating the database, or Ctrl+C to cancel..."
fi

echo ""
echo "=========================================="
echo "Next Steps:"
echo "=========================================="
echo ""
echo "1. Update your .env file with:"
echo "   DATABASE_URL_TEST=postgresql+psycopg://postgres:postgres@localhost:5432/scoped_memory_test"
echo ""
echo "   (Replace 'postgres:postgres' with your actual username:password if different)"
echo ""
echo "2. Verify connection:"
echo "   ./check_test_db.sh"
echo ""
echo "3. Run tests:"
echo "   ./run_tests.sh"
echo ""

