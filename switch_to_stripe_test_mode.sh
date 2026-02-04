#!/bin/bash

# Switch Stripe Configuration to Test Mode
# This script helps you update your Stripe keys to test mode

set -e

echo "🔄 Switching Stripe to Test Mode"
echo ""

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "❌ .env file not found!"
    exit 1
fi

echo "📋 Current Stripe configuration:"
if grep -q "STRIPE_SECRET_KEY" .env; then
    CURRENT_KEY=$(grep "STRIPE_SECRET_KEY" .env | cut -d'=' -f2 | head -c 10)
    echo "   Current key starts with: $CURRENT_KEY"
    if [[ "$CURRENT_KEY" == "sk_live" ]]; then
        echo "   ⚠️  Currently using LIVE mode"
    elif [[ "$CURRENT_KEY" == "sk_test" ]]; then
        echo "   ✅ Already in TEST mode"
        exit 0
    fi
else
    echo "   ⚠️  No STRIPE_SECRET_KEY found in .env"
fi

echo ""
echo "📝 To switch to TEST mode, you need to:"
echo ""
echo "1. Get your TEST mode keys from Stripe Dashboard:"
echo "   https://dashboard.stripe.com/test/apikeys"
echo ""
echo "2. Update your .env file with TEST keys:"
echo "   STRIPE_SECRET_KEY=sk_test_..."
echo "   STRIPE_PUBLISHABLE_KEY=pk_test_..."
echo "   STRIPE_WEBHOOK_SECRET=whsec_... (from test webhook)"
echo ""
echo "3. Update your .env.deploy file with TEST keys (for Cloud Run)"
echo ""
echo "4. Redeploy the API:"
echo "   ./deploy-all.sh --api-only"
echo ""
echo "⚠️  IMPORTANT: Make sure to get a new webhook secret for TEST mode!"
echo "   Test webhooks are separate from live webhooks in Stripe."
echo ""
read -p "Do you have your TEST mode keys ready? (y/n) " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    echo "Please provide your TEST mode keys:"
    echo ""
    read -p "STRIPE_SECRET_KEY (sk_test_...): " TEST_SECRET_KEY
    read -p "STRIPE_PUBLISHABLE_KEY (pk_test_...): " TEST_PUBLISHABLE_KEY
    read -p "STRIPE_WEBHOOK_SECRET (whsec_...): " TEST_WEBHOOK_SECRET
    
    if [ -z "$TEST_SECRET_KEY" ] || [ -z "$TEST_PUBLISHABLE_KEY" ] || [ -z "$TEST_WEBHOOK_SECRET" ]; then
        echo "❌ All keys are required!"
        exit 1
    fi
    
    # Update .env file
    echo ""
    echo "📝 Updating .env file..."
    if grep -q "STRIPE_SECRET_KEY=" .env; then
        sed -i '' "s|STRIPE_SECRET_KEY=.*|STRIPE_SECRET_KEY=$TEST_SECRET_KEY|" .env
    else
        echo "STRIPE_SECRET_KEY=$TEST_SECRET_KEY" >> .env
    fi
    
    if grep -q "STRIPE_PUBLISHABLE_KEY=" .env; then
        sed -i '' "s|STRIPE_PUBLISHABLE_KEY=.*|STRIPE_PUBLISHABLE_KEY=$TEST_PUBLISHABLE_KEY|" .env
    else
        echo "STRIPE_PUBLISHABLE_KEY=$TEST_PUBLISHABLE_KEY" >> .env
    fi
    
    if grep -q "STRIPE_WEBHOOK_SECRET=" .env; then
        sed -i '' "s|STRIPE_WEBHOOK_SECRET=.*|STRIPE_WEBHOOK_SECRET=$TEST_WEBHOOK_SECRET|" .env
    else
        echo "STRIPE_WEBHOOK_SECRET=$TEST_WEBHOOK_SECRET" >> .env
    fi
    
    echo "✅ .env file updated"
    
    # Update .env.deploy file
    if [ -f ".env.deploy" ]; then
        echo "📝 Updating .env.deploy file..."
        if grep -q "STRIPE_SECRET_KEY=" .env.deploy; then
            sed -i '' "s|STRIPE_SECRET_KEY=.*|STRIPE_SECRET_KEY=$TEST_SECRET_KEY|" .env.deploy
        else
            echo "export STRIPE_SECRET_KEY=$TEST_SECRET_KEY" >> .env.deploy
        fi
        
        if grep -q "STRIPE_PUBLISHABLE_KEY=" .env.deploy; then
            sed -i '' "s|STRIPE_PUBLISHABLE_KEY=.*|STRIPE_PUBLISHABLE_KEY=$TEST_PUBLISHABLE_KEY|" .env.deploy
        else
            echo "export STRIPE_PUBLISHABLE_KEY=$TEST_PUBLISHABLE_KEY" >> .env.deploy
        fi
        
        if grep -q "STRIPE_WEBHOOK_SECRET=" .env.deploy; then
            sed -i '' "s|STRIPE_WEBHOOK_SECRET=.*|STRIPE_WEBHOOK_SECRET=$TEST_WEBHOOK_SECRET|" .env.deploy
        else
            echo "export STRIPE_WEBHOOK_SECRET=$TEST_WEBHOOK_SECRET" >> .env.deploy
        fi
        
        echo "✅ .env.deploy file updated"
    else
        echo "⚠️  .env.deploy file not found. You'll need to update it manually."
    fi
    
    echo ""
    echo "✅ Stripe keys updated to TEST mode!"
    echo ""
    echo "📋 Next steps:"
    echo "1. Restart local Docker services: docker compose restart api"
    echo "2. Redeploy API to Cloud Run: ./deploy-all.sh --api-only"
    echo ""
else
    echo ""
    echo "📝 Manual instructions:"
    echo ""
    echo "1. Get TEST keys from: https://dashboard.stripe.com/test/apikeys"
    echo "2. Update .env and .env.deploy files manually"
    echo "3. Redeploy API"
fi

