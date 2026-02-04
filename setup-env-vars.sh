#!/bin/bash

# Memory Scope - Environment Variables Setup Script
# This script helps you set up environment variables for deployment

set -e

echo "🔐 Setting up environment variables for deployment..."
echo ""

# Stripe Secret Key - set your key from https://dashboard.stripe.com/apikeys
# export STRIPE_SECRET_KEY="sk_test_..." or sk_live_...
if [ -n "$STRIPE_SECRET_KEY" ]; then
    echo "✅ STRIPE_SECRET_KEY set"
else
    echo "⚠️  Set STRIPE_SECRET_KEY before deploying (see env.example)"
fi

# Check for other required variables
echo ""
echo "📋 Checking required environment variables..."
echo ""

MISSING_VARS=()

if [ -z "$DATABASE_URL" ]; then
    MISSING_VARS+=("DATABASE_URL")
    echo "❌ DATABASE_URL not set"
    echo "   You need a PostgreSQL database."
    echo "   Options:"
    echo "   1. Supabase (free): https://supabase.com"
    echo "   2. Railway: https://railway.app (includes PostgreSQL)"
    echo "   3. Google Cloud SQL: gcloud sql instances create ..."
    echo ""
else
    echo "✅ DATABASE_URL is set"
fi

if [ -z "$FIREBASE_SERVICE_ACCOUNT_JSON" ]; then
    MISSING_VARS+=("FIREBASE_SERVICE_ACCOUNT_JSON")
    echo "❌ FIREBASE_SERVICE_ACCOUNT_JSON not set"
    echo "   Get it from:"
    echo "   https://console.firebase.google.com/project/scoped-memory-7c9f9/settings/serviceaccounts/adminsdk"
    echo "   Click 'Generate new private key'"
    echo ""
else
    echo "✅ FIREBASE_SERVICE_ACCOUNT_JSON is set"
fi

if [ -z "$STRIPE_PUBLISHABLE_KEY" ]; then
    echo "⚠️  STRIPE_PUBLISHABLE_KEY not set (optional for backend)"
    echo "   Get it from: https://dashboard.stripe.com/apikeys"
    echo ""
else
    echo "✅ STRIPE_PUBLISHABLE_KEY is set"
fi

echo ""
if [ ${#MISSING_VARS[@]} -eq 0 ]; then
    echo "✅ All required environment variables are set!"
    echo ""
    echo "🚀 Ready to deploy! Run:"
    echo "   ./deploy-backend-cloudrun.sh"
else
    echo "⚠️  Missing required variables: $(IFS=' '; echo "${MISSING_VARS[*]}")"
    echo ""
    echo "📝 To set them, run:"
    for var in "${MISSING_VARS[@]}"; do
        if [ "$var" == "DATABASE_URL" ]; then
            echo "   export DATABASE_URL=\"postgresql+psycopg://user:pass@host:5432/memory_scope\""
        elif [ "$var" == "FIREBASE_SERVICE_ACCOUNT_JSON" ]; then
            echo "   export FIREBASE_SERVICE_ACCOUNT_JSON='{\"type\":\"service_account\",...}'"
        fi
    done
    echo ""
    echo "Or set them in this script and run it again."
fi

echo ""
echo "💡 Tip: Add these to your shell profile (~/.zshrc) to persist them:"
echo "   export STRIPE_SECRET_KEY=\"$STRIPE_SECRET_KEY\""
if [ -n "$DATABASE_URL" ]; then
    echo "   export DATABASE_URL=\"$DATABASE_URL\""
fi
if [ -n "$FIREBASE_SERVICE_ACCOUNT_JSON" ]; then
    echo "   export FIREBASE_SERVICE_ACCOUNT_JSON='...'"
fi

