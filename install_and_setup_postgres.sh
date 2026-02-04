#!/bin/bash
# Install PostgreSQL and set up test database (macOS with Homebrew)

set -e

echo "=========================================="
echo "PostgreSQL Installation & Setup"
echo "=========================================="
echo ""

# Check if Homebrew is installed
if ! command -v brew &> /dev/null; then
    echo "❌ Homebrew not found!"
    echo "Install Homebrew first: https://brew.sh"
    exit 1
fi

echo "✓ Homebrew found"
echo ""

# Check if PostgreSQL is already installed
if command -v psql &> /dev/null; then
    echo "✓ PostgreSQL already installed: $(psql --version)"
    echo ""
else
    echo "Installing PostgreSQL..."
    brew install postgresql@16
    echo "✓ PostgreSQL installed"
    echo ""
fi

# Start PostgreSQL service
echo "Starting PostgreSQL service..."
brew services start postgresql@16
sleep 3  # Give it time to start
echo "✓ PostgreSQL service started"
echo ""

# Check if PostgreSQL is running
if ! pg_isready -h localhost -p 5432 > /dev/null 2>&1; then
    echo "⚠ PostgreSQL might still be starting. Waiting a bit more..."
    sleep 5
    if ! pg_isready -h localhost -p 5432 > /dev/null 2>&1; then
        echo "❌ PostgreSQL is not responding"
        echo "Try manually: brew services restart postgresql@16"
        exit 1
    fi
fi

echo "✓ PostgreSQL is running"
echo ""

# Create test database
echo "Creating test database 'scoped_memory_test'..."

# Try different connection methods
if createdb scoped_memory_test 2>/dev/null; then
    echo "✓ Test database created"
elif psql -U postgres -h localhost -c "CREATE DATABASE scoped_memory_test;" 2>/dev/null; then
    echo "✓ Test database created"
elif psql -h localhost -c "CREATE DATABASE scoped_memory_test;" 2>/dev/null; then
    echo "✓ Test database created"
else
    echo "⚠ Could not create database automatically"
    echo ""
    echo "Please create it manually:"
    echo "  createdb scoped_memory_test"
    echo ""
    echo "Or:"
    echo "  psql -U postgres"
    echo "  CREATE DATABASE scoped_memory_test;"
    echo "  \\q"
    echo ""
    read -p "Press Enter after creating the database, or Ctrl+C to cancel..."
fi

echo ""
echo "=========================================="
echo "Configuration"
echo "=========================================="
echo ""

# Get current user for connection string
CURRENT_USER=$(whoami)

# Update .env file
ENV_FILE=".env"
if [ -f "$ENV_FILE" ]; then
    # Check if DATABASE_URL_TEST already exists
    if grep -q "DATABASE_URL_TEST" "$ENV_FILE"; then
        echo "Updating existing DATABASE_URL_TEST in .env..."
        # Use sed to update (works on macOS)
        if [[ "$OSTYPE" == "darwin"* ]]; then
            sed -i '' "s|DATABASE_URL_TEST=.*|DATABASE_URL_TEST=postgresql+psycopg://$CURRENT_USER:@localhost:5432/scoped_memory_test|" "$ENV_FILE"
        else
            sed -i "s|DATABASE_URL_TEST=.*|DATABASE_URL_TEST=postgresql+psycopg://$CURRENT_USER:@localhost:5432/scoped_memory_test|" "$ENV_FILE"
        fi
    else
        echo "Adding DATABASE_URL_TEST to .env..."
        echo "" >> "$ENV_FILE"
        echo "DATABASE_URL_TEST=postgresql+psycopg://$CURRENT_USER:@localhost:5432/scoped_memory_test" >> "$ENV_FILE"
    fi
    echo "✓ .env file updated"
else
    echo "Creating .env file..."
    cat > "$ENV_FILE" << EOF
DATABASE_URL=postgresql+psycopg://$CURRENT_USER:@localhost:5432/scoped_memory
DATABASE_URL_TEST=postgresql+psycopg://$CURRENT_USER:@localhost:5432/scoped_memory_test
API_KEY_SALT_ROUNDS=12
LOG_LEVEL=INFO
EOF
    echo "✓ .env file created"
fi

echo ""
echo "=========================================="
echo "Setup Complete! ✓"
echo "=========================================="
echo ""
echo "Next steps:"
echo ""
echo "1. Verify connection:"
echo "   ./check_test_db.sh"
echo ""
echo "2. Run tests:"
echo "   ./run_tests.sh"
echo ""
echo "Note: If you get authentication errors, you might need to:"
echo "  - Set a password for your PostgreSQL user"
echo "  - Or update .env to use: postgresql+psycopg://postgres:postgres@localhost:5432/scoped_memory_test"
echo ""

