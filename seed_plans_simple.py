#!/usr/bin/env python3
"""Simple script to seed subscription plans without Stripe dependency."""
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import Session
from app.database import get_db
from app.models import SubscriptionPlan

def seed_plans():
    """Seed subscription plans."""
    db: Session = next(get_db())
    
    try:
        plans = [
            {
                "name": "free",
                "display_name": "Free",
                "price_monthly": 0,
                "price_yearly": 0,
                "requests_per_month": 10000,
                "memories_limit": 1000,
                "rate_limit_per_hour": 1000,
                "features": [
                    "10,000 API calls/month",
                    "1,000 memories stored",
                    "All core features",
                    "Community support",
                ],
            },
            {
                "name": "pro",
                "display_name": "Pro",
                "price_monthly": 99.00,
                "price_yearly": 990.00,
                "requests_per_month": 100000,
                "memories_limit": 1000000,
                "rate_limit_per_hour": 10000,
                "features": [
                    "100,000 API calls/month",
                    "1,000,000 memories stored",
                    "All core features",
                    "Priority support",
                    "Higher rate limits",
                ],
            },
            {
                "name": "enterprise",
                "display_name": "Enterprise",
                "price_monthly": 999.00,
                "price_yearly": 9990.00,
                "requests_per_month": -1,  # Unlimited
                "memories_limit": -1,  # Unlimited
                "rate_limit_per_hour": 100000,
                "features": [
                    "Unlimited API calls",
                    "Unlimited memories",
                    "All core features",
                    "Dedicated support",
                    "Custom rate limits",
                ],
            },
        ]
        
        for plan_data in plans:
            existing = db.query(SubscriptionPlan).filter(SubscriptionPlan.name == plan_data["name"]).first()
            if not existing:
                plan = SubscriptionPlan(**plan_data)
                db.add(plan)
                print(f"✅ Created {plan_data['display_name']} plan")
            else:
                print(f"✓ {plan_data['display_name']} plan already exists")
        
        db.commit()
        print("\n✅ Subscription plans seeded successfully!")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    seed_plans()

