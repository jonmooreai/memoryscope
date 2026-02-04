#!/bin/bash
# Script to verify and clear all subscriptions

set -e

echo "🔍 Checking current subscriptions..."
python3 -m app.clear_subscription_data --list

echo ""
echo "🗑️  Clearing ALL subscriptions..."
echo "yes" | python3 -m app.clear_subscription_data --all

echo ""
echo "✅ Verification - checking subscriptions again..."
python3 -m app.clear_subscription_data --list

echo ""
echo "✅ All subscriptions cleared! Next login will create a fresh free subscription."

