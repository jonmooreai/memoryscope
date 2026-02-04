#!/bin/bash

# Memory Scope - Set All Environment Variables for Deployment
# Run this before deploying to ensure all variables are set

set -e

echo "🔐 Setting up all environment variables for deployment..."
echo ""

# Load from .env.deploy if it exists
if [ -f .env.deploy ]; then
    echo "📂 Loading variables from .env.deploy..."
    source .env.deploy
    echo "✅ Loaded from .env.deploy"
else
    # Stripe Secret Key - set in .env.deploy or here
    echo "⚠️  Set STRIPE_SECRET_KEY in .env.deploy or export it before deploying"
fi

# Firebase Service Account JSON (set path to your service account JSON)
FIREBASE_JSON_FILE="${FIREBASE_SERVICE_ACCOUNT_PATH:-/path/to/your-firebase-adminsdk.json}"
if [ -f "$FIREBASE_JSON_FILE" ]; then
    export FIREBASE_SERVICE_ACCOUNT_JSON=$(python3 -c "
import json
import sys
with open('$FIREBASE_JSON_FILE', 'r') as f:
    data = json.load(f)
    print(json.dumps(data))
")
    echo "✅ FIREBASE_SERVICE_ACCOUNT_JSON set from file"
else
    echo "⚠️  Firebase JSON file not found at: $FIREBASE_JSON_FILE"
fi

# Database URL (check if set)
if [ -z "$DATABASE_URL" ]; then
    echo ""
    echo "❌ DATABASE_URL not set"
    echo "   You need to set this before deploying."
    echo "   Get it from Supabase, Railway, or Cloud SQL"
    echo ""
    echo "   Example:"
    echo "   export DATABASE_URL=\"postgresql+psycopg://user:pass@host:5432/memory_scope\""
    echo ""
else
    echo "✅ DATABASE_URL is set"
fi

echo ""
echo "📋 Summary:"
echo "   ✅ STRIPE_SECRET_KEY: ${STRIPE_SECRET_KEY:0:20}..."
echo "   ✅ FIREBASE_SERVICE_ACCOUNT_JSON: Set ($(echo -n "$FIREBASE_SERVICE_ACCOUNT_JSON" | wc -c | tr -d ' ') chars)"
if [ -n "$DATABASE_URL" ]; then
    echo "   ✅ DATABASE_URL: Set"
else
    echo "   ❌ DATABASE_URL: Not set (REQUIRED)"
fi

echo ""
if [ -n "$DATABASE_URL" ]; then
    echo "✅ All required environment variables are set!"
    echo ""
    echo "🚀 Ready to deploy! Run:"
    echo "   ./deploy-backend-cloudrun.sh"
else
    echo "⚠️  DATABASE_URL is still required before deploying."
    echo ""
    echo "💡 Quick setup with Supabase:"
    echo "   1. Go to https://supabase.com"
    echo "   2. Create project"
    echo "   3. Copy connection string from Settings → Database"
    echo "   4. Run: export DATABASE_URL=\"postgresql+psycopg://...\""
    echo "   5. Then run: ./deploy-backend-cloudrun.sh"
fi

