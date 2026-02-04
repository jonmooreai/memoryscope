"""
Seed script to add realistic test data for 1jonmoore@gmail.com
Run with: python -m app.seed_test_data
"""
import uuid
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import App, Memory, AuditEvent, ReadGrant
from app.utils import hash_api_key, hash_revocation_token, normalize_purpose
from app.config import settings

# Test user email
TEST_USER_EMAIL = "1jonmoore@gmail.com"
# For Firebase, we'll use a consistent UID - in production this would come from Firebase
TEST_USER_ID = "test_user_jonmoore"  # This would be the Firebase UID in production


def create_test_data():
    """Create realistic test data for the test user."""
    db: Session = SessionLocal()
    
    try:
        # Create test API keys
        print("Creating test API keys...")
        
        # Production API Key
        prod_api_key = "sk_live_prod_" + uuid.uuid4().hex[:32]
        prod_app = App(
            id=uuid.uuid4(),
            name="Production Key",
            api_key_hash=hash_api_key(prod_api_key, settings.api_key_salt_rounds),
            created_at=datetime.utcnow() - timedelta(days=30),
        )
        db.add(prod_app)
        db.flush()
        print(f"  Created Production Key: {prod_api_key}")
        
        # Development API Key
        dev_api_key = "sk_live_dev_" + uuid.uuid4().hex[:32]
        dev_app = App(
            id=uuid.uuid4(),
            name="Development Key",
            api_key_hash=hash_api_key(dev_api_key, settings.api_key_salt_rounds),
            created_at=datetime.utcnow() - timedelta(days=15),
        )
        db.add(dev_app)
        db.flush()
        print(f"  Created Development Key: {dev_api_key}")
        
        # Create test memories
        print("Creating test memories...")
        
        memories_data = [
            {
                "user_id": TEST_USER_ID,
                "scope": "preferences",
                "domain": "food",
                "value_json": {"likes": ["pizza", "sushi", "tacos"], "dislikes": ["broccoli", "spinach"]},
                "value_shape": "likes_dislikes",
                "source": "explicit_user_input",
                "ttl_days": 30,
                "app_id": prod_app.id,
            },
            {
                "user_id": TEST_USER_ID,
                "scope": "preferences",
                "domain": "food",
                "value_json": {"likes": ["burgers", "pasta"], "dislikes": ["mushrooms"]},
                "value_shape": "likes_dislikes",
                "source": "explicit_user_input",
                "ttl_days": 30,
                "app_id": prod_app.id,
            },
            {
                "user_id": TEST_USER_ID,
                "scope": "constraints",
                "domain": "dietary",
                "value_json": ["vegetarian", "no nuts", "gluten-free"],
                "value_shape": "rules_list",
                "source": "explicit_user_input",
                "ttl_days": 90,
                "app_id": prod_app.id,
            },
            {
                "user_id": TEST_USER_ID,
                "scope": "communication",
                "domain": None,
                "value_json": {"preferred_tone": "friendly", "use_emojis": True, "formality": "casual"},
                "value_shape": "kv_map",
                "source": "explicit_user_input",
                "ttl_days": 60,
                "app_id": prod_app.id,
            },
            {
                "user_id": TEST_USER_ID,
                "scope": "accessibility",
                "domain": None,
                "value_json": {"high_contrast": True, "font_size": "large", "screen_reader": False},
                "value_shape": "boolean_flags",
                "source": "explicit_user_input",
                "ttl_days": 90,
                "app_id": prod_app.id,
            },
            {
                "user_id": TEST_USER_ID,
                "scope": "schedule",
                "domain": "work",
                "value_json": [
                    {"day": "monday", "start": "09:00", "end": "17:00"},
                    {"day": "tuesday", "start": "09:00", "end": "17:00"},
                    {"day": "wednesday", "start": "09:00", "end": "17:00"},
                ],
                "value_shape": "schedule_windows",
                "source": "explicit_user_input",
                "ttl_days": 30,
                "app_id": prod_app.id,
            },
        ]
        
        created_memories = []
        for mem_data in memories_data:
            created_at = datetime.utcnow() - timedelta(days=mem_data["ttl_days"] - 5)
            expires_at = created_at + timedelta(days=mem_data["ttl_days"])
            
            memory = Memory(
                id=uuid.uuid4(),
                user_id=mem_data["user_id"],
                scope=mem_data["scope"],
                domain=mem_data["domain"],
                value_json=mem_data["value_json"],
                value_shape=mem_data["value_shape"],
                source=mem_data["source"],
                ttl_days=mem_data["ttl_days"],
                created_at=created_at,
                expires_at=expires_at,
                app_id=mem_data["app_id"],
            )
            db.add(memory)
            created_memories.append(memory)
        
        db.flush()
        print(f"  Created {len(created_memories)} memories")
        
        # Create test audit events (for analytics)
        print("Creating test audit events...")
        
        # Generate events over the last 30 days
        event_types = ["MEMORY_CREATE", "MEMORY_READ", "MEMORY_READ", "MEMORY_READ", "MEMORY_REVOKE"]
        scopes = ["preferences", "constraints", "communication", "accessibility", "schedule"]
        purposes = [
            "generate food recommendations",
            "check dietary restrictions",
            "personalize communication",
            "render UI with accessibility settings",
            "schedule meeting",
        ]
        
        audit_events = []
        for i in range(150):  # 150 events over 30 days
            days_ago = i % 30
            hours_ago = i % 24
            timestamp = datetime.utcnow() - timedelta(days=days_ago, hours=hours_ago)
            
            event_type = event_types[i % len(event_types)]
            scope = scopes[i % len(scopes)]
            purpose = purposes[i % len(purposes)]
            purpose_class = normalize_purpose(purpose)
            
            # Use prod_app for most events, dev_app for some
            app_id = prod_app.id if i % 5 != 0 else dev_app.id
            
            event = AuditEvent(
                id=uuid.uuid4(),
                timestamp=timestamp,
                event_type=event_type,
                user_id=TEST_USER_ID,
                app_id=app_id,
                scope=scope,
                domain="food" if scope == "preferences" else None,
                purpose=purpose if event_type == "MEMORY_READ" else None,
                purpose_class=purpose_class if event_type == "MEMORY_READ" else None,
                memory_ids=[created_memories[i % len(created_memories)].id] if event_type in ["MEMORY_CREATE", "MEMORY_READ"] else None,
                reason_code=None if i % 20 != 0 else "POLICY_DENIED",
            )
            db.add(event)
            audit_events.append(event)
        
        db.flush()
        print(f"  Created {len(audit_events)} audit events")
        
        # Create test read grants
        print("Creating test read grants...")
        
        read_grants = []
        for i in range(20):
            days_ago = i % 10
            created_at = datetime.utcnow() - timedelta(days=days_ago)
            expires_at = created_at + timedelta(days=30)
            
            revocation_token = f"rev_{uuid.uuid4().hex}"
            scope = scopes[i % len(scopes)]
            purpose = purposes[i % len(purposes)]
            purpose_class = normalize_purpose(purpose)
            
            grant = ReadGrant(
                id=uuid.uuid4(),
                revocation_token_hash=hash_revocation_token(revocation_token),
                user_id=TEST_USER_ID,
                app_id=prod_app.id,
                scope=scope,
                domain="food" if scope == "preferences" else None,
                purpose=purpose,
                purpose_class=purpose_class,
                max_age_days=30,
                created_at=created_at,
                expires_at=expires_at,
                revoked_at=None if i % 5 != 0 else created_at + timedelta(days=2),
                revoke_reason="user_requested" if i % 5 == 0 else None,
            )
            db.add(grant)
            read_grants.append(grant)
        
        db.flush()
        print(f"  Created {len(read_grants)} read grants")
        
        # Commit all changes
        db.commit()
        print("\n✅ Test data created successfully!")
        print(f"\nTest User: {TEST_USER_EMAIL}")
        print(f"User ID: {TEST_USER_ID}")
        print(f"\nAPI Keys created:")
        print(f"  Production: {prod_api_key}")
        print(f"  Development: {dev_api_key}")
        print(f"\nSummary:")
        print(f"  - {len(created_memories)} memories")
        print(f"  - {len(audit_events)} audit events")
        print(f"  - {len(read_grants)} read grants")
        
    except Exception as e:
        db.rollback()
        print(f"\n❌ Error creating test data: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    create_test_data()

