#!/usr/bin/env python3
"""
Create realistic test data for 1jonmoore@gmail.com user.
This script creates:
- A subscription (Pro plan)
- API keys
- Audit events (API calls) - 85% of limit to trigger warnings
- Memories - 82% of limit to trigger warnings
- Overage settings
"""
import sys
import os
from datetime import datetime, timedelta
from uuid import uuid4

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import Session
from app.database import get_db
from app.models import App, Memory, AuditEvent, Subscription, SubscriptionPlan
import hashlib

# Test user ID (Firebase UID for 1jonmoore@gmail.com)
TEST_USER_ID = "test_user_jonmoore"
TEST_EMAIL = "1jonmoore@gmail.com"

def create_test_data():
    """Create comprehensive test data for the test user."""
    db: Session = next(get_db())
    
    try:
        print(f"Creating test data for user: {TEST_EMAIL} (ID: {TEST_USER_ID})")
        
        # 1. Get or create Pro subscription
        print("\n1. Setting up Pro subscription...")
        subscription = db.query(Subscription).filter(Subscription.user_id == TEST_USER_ID).first()
        
        if not subscription:
            # Get Pro plan
            pro_plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.name == "pro").first()
            if not pro_plan:
                print("❌ Pro plan not found. Please run seed_subscription_plans.py first.")
                return
            
            # Create subscription
            now = datetime.utcnow()
            subscription = Subscription(
                user_id=TEST_USER_ID,
                plan_id=pro_plan.id,
                status="active",
                current_period_start=now - timedelta(days=15),  # 15 days into billing period
                current_period_end=now + timedelta(days=15),
                overage_enabled=True,
                overage_limit=50000,  # 50k overage calls
            )
            db.add(subscription)
            db.commit()
            db.refresh(subscription)
            print("✅ Created Pro subscription")
        else:
            # Update existing subscription
            subscription.overage_enabled = True
            subscription.overage_limit = 50000
            subscription.status = "active"
            db.commit()
            db.refresh(subscription)
            print("✅ Updated existing subscription")
        
        plan = subscription.plan
        api_calls_limit = plan.requests_per_month
        storage_limit = plan.memories_limit
        
        # Calculate target usage (85% for API calls, 82% for storage to trigger warnings)
        target_api_calls = int(api_calls_limit * 0.85)
        target_storage = int(storage_limit * 0.82)
        
        print(f"\n2. Target usage:")
        print(f"   API Calls: {target_api_calls:,} / {api_calls_limit:,} (85%)")
        print(f"   Storage: {target_storage:,} / {storage_limit:,} (82%)")
        
        # 2. Get or create an app
        print("\n3. Setting up API key...")
        app = db.query(App).filter(App.user_id == TEST_USER_ID).first()
        
        if not app:
            # Create API key
            api_key = f"test_key_{uuid4().hex[:16]}"
            api_key_hash = hashlib.sha256(api_key.encode()).hexdigest()
            
            app = App(
                name="Test App",
                api_key_hash=api_key_hash,
                user_id=TEST_USER_ID,
            )
            db.add(app)
            db.commit()
            db.refresh(app)
            print(f"✅ Created app with API key: {api_key}")
        else:
            print("✅ Using existing app")
        
        # 3. Count existing audit events in current period
        period_start = subscription.current_period_start
        existing_calls = db.query(AuditEvent).filter(
            AuditEvent.user_id == TEST_USER_ID,
            AuditEvent.timestamp >= period_start,
            AuditEvent.event_type.in_(["memory_create", "memory_read", "memory_read_continue"])
        ).count()
        
        # 4. Create audit events (API calls) to reach target
        print(f"\n4. Creating audit events...")
        calls_needed = max(0, target_api_calls - existing_calls)
        
        if calls_needed > 0:
            events = []
            now = datetime.utcnow()
            # Spread events over the billing period
            for i in range(calls_needed):
                # Distribute events over the period
                days_ago = (i % 15)  # Spread over 15 days
                timestamp = period_start + timedelta(days=days_ago, hours=i % 24)
                
                # Mix of event types
                event_type = ["memory_create", "memory_read", "memory_read_continue"][i % 3]
                
                event = AuditEvent(
                    timestamp=timestamp,
                    event_type=event_type,
                    user_id=TEST_USER_ID,
                    app_id=app.id,
                    scope="user_preferences",
                    domain="example.com",
                    purpose="personalization",
                    purpose_class="personalization",
                )
                events.append(event)
            
            db.bulk_save_objects(events)
            db.commit()
            print(f"✅ Created {calls_needed:,} audit events")
        else:
            print(f"✅ Already have {existing_calls:,} audit events (target: {target_api_calls:,})")
        
        # 5. Count existing memories
        existing_memories = db.query(Memory).filter(
            Memory.user_id == TEST_USER_ID,
            Memory.expires_at > datetime.utcnow()
        ).count()
        
        # 6. Create memories to reach target
        print(f"\n5. Creating memories...")
        memories_needed = max(0, target_storage - existing_memories)
        
        if memories_needed > 0:
            memories = []
            now = datetime.utcnow()
            
            for i in range(memories_needed):
                memory = Memory(
                    user_id=TEST_USER_ID,
                    scope="user_preferences",
                    domain="example.com",
                    value_json={
                        "preference": f"test_preference_{i}",
                        "value": f"test_value_{i}",
                    },
                    value_shape="key_value",
                    source="test",
                    ttl_days=30,
                    created_at=now - timedelta(days=i % 10),
                    expires_at=now + timedelta(days=30 - (i % 10)),
                    app_id=app.id,
                )
                memories.append(memory)
            
            db.bulk_save_objects(memories)
            db.commit()
            print(f"✅ Created {memories_needed:,} memories")
        else:
            print(f"✅ Already have {existing_memories:,} memories (target: {target_storage:,})")
        
        # 7. Verify final counts
        final_calls = db.query(AuditEvent).filter(
            AuditEvent.user_id == TEST_USER_ID,
            AuditEvent.timestamp >= period_start,
            AuditEvent.event_type.in_(["memory_create", "memory_read", "memory_read_continue"])
        ).count()
        
        final_memories = db.query(Memory).filter(
            Memory.user_id == TEST_USER_ID,
            Memory.expires_at > datetime.utcnow()
        ).count()
        
        calls_percentage = (final_calls / api_calls_limit * 100) if api_calls_limit > 0 else 0
        storage_percentage = (final_memories / storage_limit * 100) if storage_limit > 0 else 0
        
        print(f"\n✅ Test data created successfully!")
        print(f"\nFinal usage:")
        print(f"   API Calls: {final_calls:,} / {api_calls_limit:,} ({calls_percentage:.1f}%)")
        print(f"   Storage: {final_memories:,} / {storage_limit:,} ({storage_percentage:.1f}%)")
        print(f"   Overage Enabled: {subscription.overage_enabled}")
        print(f"   Overage Limit: {subscription.overage_limit:,}")
        
        if calls_percentage >= 80:
            print(f"\n⚠️  API calls warning threshold reached (80%+)")
        if storage_percentage >= 80:
            print(f"⚠️  Storage warning threshold reached (80%+)")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error creating test data: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    create_test_data()

