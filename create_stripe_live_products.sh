#!/bin/bash

# Create Stripe Products in Live Mode
# This script clears existing Stripe IDs and creates fresh products in Live mode

set -e

echo "🔧 Creating Stripe products in LIVE mode..."
echo ""

# Check if .env has LIVE key
if ! grep -q "STRIPE_SECRET_KEY=sk_live" .env; then
    echo "❌ ERROR: Your .env file doesn't have a LIVE Stripe key!"
    echo "   Current key type: $(grep STRIPE_SECRET_KEY .env | grep -o 'sk_[a-z]*')"
    echo ""
    echo "   Make sure your .env has:"
    echo "   STRIPE_SECRET_KEY=sk_live_..."
    exit 1
fi

echo "✅ Verified: Using LIVE Stripe key"
echo ""

# Load environment variables
export $(grep -v '^#' .env | xargs)

# Run Python script to create products
echo "📦 Creating products in Stripe..."
python3 << 'PYTHON_SCRIPT'
import os
import sys
import stripe
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import SubscriptionPlan
from app.billing import BillingService

# Initialize Stripe with LIVE key
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
stripe.api_version = "2023-10-16"

if not stripe.api_key or not stripe.api_key.startswith("sk_live"):
    print("❌ ERROR: Not using LIVE Stripe key!")
    print(f"   Key starts with: {stripe.api_key[:10] if stripe.api_key else 'None'}...")
    sys.exit(1)

print("🔧 Setting up Stripe products in LIVE mode...")
print("")

db: Session = SessionLocal()

try:
    # Process Pro plan
    plan_name = "pro"
    plan_def = BillingService.PLAN_DEFINITIONS[plan_name]
    
    plan = db.query(SubscriptionPlan).filter(
        SubscriptionPlan.name == plan_name
    ).first()
    
    if not plan:
        print(f"❌ Plan '{plan_name}' not found in database. Run seed_subscription_plans.py first.")
        sys.exit(1)
    
    print(f"Processing: {plan_def['display_name']} plan")
    
    # Clear existing Stripe IDs to force creation of new ones
    print("  Clearing existing Stripe IDs...")
    plan.stripe_product_id = None
    plan.stripe_price_id_monthly = None
    plan.stripe_price_id_yearly = None
    db.commit()
    
    # Create product
    print(f"  Creating Stripe product...")
    product = stripe.Product.create(
        name=plan_def["display_name"],
        description=f"{plan_def['display_name']} plan for Memory Scope API",
        metadata={
            "plan_name": plan_name,
            "requests_per_month": str(plan_def["requests_per_month"]),
            "memories_limit": str(plan_def["memories_limit"]),
        }
    )
    plan.stripe_product_id = product.id
    print(f"  ✓ Created product: {product.id}")
    print(f"     Name: {product.name}")
    print(f"     View: https://dashboard.stripe.com/products/{product.id}")
    
    # Create monthly price
    print(f"  Creating monthly price (${plan_def['price_monthly']})...")
    monthly_price = stripe.Price.create(
        product=product.id,
        unit_amount=int(plan_def["price_monthly"] * 100),  # Convert to cents
        currency="usd",
        recurring={"interval": "month"},
        metadata={"plan_name": plan_name, "billing_cycle": "monthly"}
    )
    plan.stripe_price_id_monthly = monthly_price.id
    print(f"  ✓ Created monthly price: {monthly_price.id}")
    print(f"     Amount: ${plan_def['price_monthly']}/month")
    
    # Create yearly price
    if plan_def.get("price_yearly") and plan_def["price_yearly"] > 0:
        print(f"  Creating yearly price (${plan_def['price_yearly']})...")
        yearly_price = stripe.Price.create(
            product=product.id,
            unit_amount=int(plan_def["price_yearly"] * 100),  # Convert to cents
            currency="usd",
            recurring={"interval": "year"},
            metadata={"plan_name": plan_name, "billing_cycle": "yearly"}
        )
        plan.stripe_price_id_yearly = yearly_price.id
        print(f"  ✓ Created yearly price: {yearly_price.id}")
        print(f"     Amount: ${plan_def['price_yearly']}/year")
    
    # Save to database
    db.commit()
    print("")
    print("✅ Successfully created Stripe products in LIVE mode!")
    print("")
    print("📋 Summary:")
    print(f"   Product ID: {product.id}")
    print(f"   Monthly Price: {monthly_price.id}")
    if plan_def.get("price_yearly") and plan_def["price_yearly"] > 0:
        print(f"   Yearly Price: {yearly_price.id}")
    print("")
    print("🌐 View in Stripe Dashboard:")
    print(f"   https://dashboard.stripe.com/products/{product.id}")
    print("")
    print("✅ Database updated with Stripe IDs")
    
except stripe.error.StripeError as e:
    db.rollback()
    print(f"❌ Stripe error: {e}")
    sys.exit(1)
except Exception as e:
    db.rollback()
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
finally:
    db.close()
PYTHON_SCRIPT

echo ""
echo "🎉 Done! Products should now appear in your Stripe Live dashboard:"
echo "   https://dashboard.stripe.com/products"
echo ""

