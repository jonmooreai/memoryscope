#!/bin/bash
# Setup Stripe webhook for local development

set -e

cd "$(dirname "$0")"

echo "🔧 Setting up Stripe webhook for local development..."
echo ""

# Check if Stripe CLI is installed
if ! command -v stripe &> /dev/null; then
    echo "❌ Stripe CLI not found"
    echo ""
    echo "Installing Stripe CLI..."
    if command -v brew &> /dev/null; then
        brew install stripe/stripe-cli/stripe
    else
        echo "Please install Stripe CLI manually: https://stripe.com/docs/stripe-cli"
        exit 1
    fi
fi

echo "✓ Stripe CLI found"
echo ""

# Check if logged in
if ! stripe config --list &> /dev/null; then
    echo "⚠️  Not logged in to Stripe CLI"
    echo ""
    echo "Please login to Stripe:"
    echo "  1. Run: stripe login"
    echo "  2. Follow the instructions to authenticate"
    echo ""
    echo "Then run this script again."
    exit 1
fi

echo "✓ Logged in to Stripe"
echo ""

# Get webhook secret from existing listener or create new one
echo "Starting webhook listener..."
echo "This will forward webhooks to: http://localhost:8000/api/v1/billing/webhook"
echo ""
echo "⚠️  Keep this terminal open while developing!"
echo "   Press Ctrl+C to stop the webhook listener"
echo ""

# Start webhook listener and extract secret
WEBHOOK_SECRET=$(stripe listen --print-secret --forward-to http://localhost:8000/api/v1/billing/webhook 2>&1 | grep -o 'whsec_[^[:space:]]*' | head -1)

if [ -z "$WEBHOOK_SECRET" ]; then
    echo ""
    echo "⚠️  Could not extract webhook secret automatically"
    echo ""
    echo "Please:"
    echo "  1. Run: stripe listen --forward-to http://localhost:8000/api/v1/billing/webhook"
    echo "  2. Copy the webhook signing secret (starts with whsec_)"
    echo "  3. Add it to .env: STRIPE_WEBHOOK_SECRET=whsec_..."
    exit 1
fi

# Update .env file
if grep -q "^STRIPE_WEBHOOK_SECRET=" .env; then
    sed -i.bak "s|^STRIPE_WEBHOOK_SECRET=.*|STRIPE_WEBHOOK_SECRET=$WEBHOOK_SECRET|" .env
    echo "✓ Updated STRIPE_WEBHOOK_SECRET in .env"
else
    echo "STRIPE_WEBHOOK_SECRET=$WEBHOOK_SECRET" >> .env
    echo "✓ Added STRIPE_WEBHOOK_SECRET to .env"
fi

echo ""
echo "✅ Webhook secret saved to .env"
echo ""
echo "Webhook secret: $WEBHOOK_SECRET"
echo ""
echo "The webhook listener is now running. Keep this terminal open."
echo "In another terminal, start your API server:"
echo "  uvicorn app.main:app --reload"
echo ""

