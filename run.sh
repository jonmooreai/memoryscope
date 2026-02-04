#!/bin/bash
# Quick start script for local development

set -e

echo "Starting Memory Scope API..."

# Check if .env exists
if [ ! -f .env ]; then
    echo "Creating .env from env.example..."
    cp env.example .env
fi

# Start PostgreSQL
echo "Starting PostgreSQL..."
docker-compose up -d

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL..."
sleep 3

# Run migrations
echo "Running migrations..."
alembic upgrade head

echo ""
echo "Setup complete! You can now:"
echo "1. API is ready (no API key required)"
echo "2. Start the server: uvicorn app.main:app --reload"
echo ""

