#!/bin/bash
# Startup script for Memory Scope API

set -e

echo "🚀 Starting Memory Scope API..."
echo ""

# Check if Docker is available
if ! command -v docker &> /dev/null; then
    echo "❌ Error: Docker is not installed or not in PATH"
    echo ""
    echo "Please install Docker Desktop:"
    echo "  https://www.docker.com/products/docker-desktop/"
    echo ""
    echo "Or via Homebrew:"
    echo "  brew install --cask docker"
    echo ""
    exit 1
fi

# Check if Docker daemon is running
if ! docker info &> /dev/null; then
    echo "❌ Error: Docker daemon is not running"
    echo ""
    echo "Please start Docker Desktop application"
    echo ""
    exit 1
fi

echo "✅ Docker is running"
echo ""

# Create .env if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env file..."
    cp env.example .env
    echo "✅ .env created"
    echo ""
fi

# Build and start services
echo "🏗️  Building and starting services..."
docker compose up -d --build

echo ""
echo "⏳ Waiting for services to be healthy..."
sleep 10

# Check service status
echo ""
docker compose ps

echo ""
echo "🏥 Checking health endpoint..."
sleep 5
curl -f http://localhost:8000/healthz && echo "" || {
    echo "❌ Health check failed. Viewing logs..."
    docker compose logs api
    exit 1
}

echo ""
echo "📊 Running migrations..."
docker compose exec api alembic upgrade head

echo ""
echo "✅ System is running!"
echo ""
echo "Next steps:"
echo "  1. Create an app:"
echo "     (no API key required)"
echo ""
echo "  2. Run tests:"
echo "     docker compose exec api pytest -q"
echo ""
echo "  3. View logs:"
echo "     docker compose logs -f api"
echo ""
echo "  4. Stop services:"
echo "     docker compose down"
echo ""
echo "API available at: http://localhost:8000"
echo "Docs available at: http://localhost:8000/docs"

