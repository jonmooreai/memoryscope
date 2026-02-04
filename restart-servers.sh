#!/bin/bash
# Restart both frontend and backend servers

set -e

echo "🛑 Stopping existing servers..."

# Kill processes on backend port (8000)
if lsof -ti:8000 > /dev/null 2>&1; then
    echo "   Stopping backend on port 8000..."
    lsof -ti:8000 | xargs kill -9 2>/dev/null || true
    sleep 1
fi

# Kill processes on frontend ports (3000 and 3001)
for port in 3000 3001; do
    if lsof -ti:$port > /dev/null 2>&1; then
        echo "   Stopping frontend on port $port..."
        lsof -ti:$port | xargs kill -9 2>/dev/null || true
        sleep 1
    fi
done

echo ""
echo "🚀 Starting servers..."

# Set Firebase credentials if available
FIREBASE_JSON_FILE="/Users/jonmoore/Downloads/scoped-memory-7c9f9-firebase-adminsdk-fbsvc-03bbb965be.json"
if [ -f "$FIREBASE_JSON_FILE" ]; then
    echo "   Setting Firebase credentials..."
    export FIREBASE_SERVICE_ACCOUNT_JSON=$(python3 -c "
import json
import sys
with open('$FIREBASE_JSON_FILE', 'r') as f:
    data = json.load(f)
    print(json.dumps(data))
")
    echo "   ✅ Firebase credentials loaded"
else
    echo "   ⚠️  Firebase service account file not found at: $FIREBASE_JSON_FILE"
    echo "   You may need to set FIREBASE_SERVICE_ACCOUNT_PATH or FIREBASE_SERVICE_ACCOUNT_JSON manually"
fi

# Start backend in background
echo "   Starting backend on port 8000..."
cd "$(dirname "$0")"
python3 -m uvicorn app.main:app --reload --port 8000 > /tmp/backend.log 2>&1 &
BACKEND_PID=$!
echo "   Backend started (PID: $BACKEND_PID)"

# Wait a moment for backend to initialize
sleep 2

# Start frontend in background
echo "   Starting frontend on port 3000..."
cd website
npm run dev > /tmp/frontend.log 2>&1 &
FRONTEND_PID=$!
echo "   Frontend started (PID: $FRONTEND_PID)"

cd ..

echo ""
echo "✅ Servers restarted!"
echo ""
echo "Backend:  http://localhost:8000"
echo "Frontend: http://localhost:3000"
echo ""
echo "Logs:"
echo "  Backend:  tail -f /tmp/backend.log"
echo "  Frontend: tail -f /tmp/frontend.log"
echo ""
echo "To stop servers:"
echo "  kill $BACKEND_PID $FRONTEND_PID"
echo "  or: lsof -ti:8000,3000 | xargs kill -9"

