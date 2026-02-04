#!/bin/bash
# Start Stripe webhook listener for local development
# This forwards webhooks from Stripe to your local API

set -e

cd "$(dirname "$0")"

echo "🔧 Starting Stripe webhook listener for local development..."
echo ""

# Check if Stripe CLI is installed
if ! command -v stripe &> /dev/null; then
    echo "❌ Stripe CLI not found"
    echo ""
    echo "Please install it:"
    echo "  brew install stripe/stripe-cli/stripe"
    exit 1
fi

# Check if logged in
if ! stripe config --list &> /dev/null 2>&1; then
    echo "⚠️  Not logged in to Stripe CLI"
    echo ""
    echo "Please login first:"
    echo "  stripe login"
    echo ""
    echo "This will open a browser for authentication."
    exit 1
fi

echo "✓ Stripe CLI ready"
echo ""

# Get the webhook secret from the listener
echo "Starting webhook listener..."
echo "Forwarding to: http://localhost:8000/api/v1/billing/webhook"
echo ""
echo "⚠️  IMPORTANT:"
echo "   1. Keep this terminal open while developing"
echo "   2. Start your API server in another terminal:"
echo "      uvicorn app.main:app --reload"
echo "   3. The webhook secret will be shown below"
echo "   4. Copy it and add to .env as STRIPE_WEBHOOK_SECRET"
echo ""

# Start the listener
stripe listen --forward-to http://localhost:8000/api/v1/billing/webhook

