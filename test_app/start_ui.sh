#!/bin/bash
# Start the test app web UI

cd "$(dirname "$0")/.."

echo "Starting Memory Scope API Test App UI..."
echo "Open your browser to: http://localhost:8080"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

python3 test_app/web_server.py

