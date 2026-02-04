#!/usr/bin/env python3
"""
Create or retrieve a default test API key for the test app UI.
"""
import sys
import os
import json
from pathlib import Path
from typing import Optional

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import App
from app.utils import hash_api_key
from app.config import settings


def get_or_create_test_app() -> tuple[str, str]:
    """
    Get or create a test app and return (app_id, api_key).
    If app already exists, returns existing key.
    """
    db: Session = SessionLocal()
    try:
        # Look for existing test app
        test_app = db.query(App).filter(App.name == "Test App (Internal)").first()
        
        if test_app:
            # App exists, but we need the original API key
            # Since we hash keys, we can't retrieve the original
            # So we'll create a new one and update the hash
            import uuid
            api_key = f"sk_test_{uuid.uuid4().hex}"
            api_key_hash = hash_api_key(api_key, settings.api_key_salt_rounds)
            
            # Update the existing app with new key hash
            test_app.api_key_hash = api_key_hash
            db.commit()
            
            return str(test_app.id), api_key
        else:
            # Create new test app
            import uuid
            api_key = f"sk_test_{uuid.uuid4().hex}"
            api_key_hash = hash_api_key(api_key, settings.api_key_salt_rounds)
            
            app = App(
                name="Test App (Internal)",
                api_key_hash=api_key_hash,
                user_id="internal_test_user",
            )
            db.add(app)
            db.commit()
            db.refresh(app)
            
            return str(app.id), api_key
            
    finally:
        db.close()


def save_test_api_key(api_key: str):
    """Save the test API key to a config file."""
    config_file = Path(__file__).parent / "test_api_key.json"
    config = {
        "api_key": api_key,
        "created_for": "Internal testing UI"
    }
    config_file.write_text(json.dumps(config, indent=2))
    # Make it readable only by owner
    os.chmod(config_file, 0o600)


def load_test_api_key() -> Optional[str]:
    """Load the test API key from config file."""
    config_file = Path(__file__).parent / "test_api_key.json"
    if config_file.exists():
        try:
            config = json.loads(config_file.read_text())
            return config.get("api_key")
        except:
            return None
    return None


if __name__ == "__main__":
    print("Setting up default test API key...")
    
    # Try to load existing key first
    existing_key = load_test_api_key()
    if existing_key:
        print(f"Found existing test API key: {existing_key[:20]}...")
        print("To create a new one, delete test_app/test_api_key.json and run this script again.")
    else:
        try:
            app_id, api_key = get_or_create_test_app()
            save_test_api_key(api_key)
            print(f"\n✓ Test API key created successfully!")
            print(f"App ID: {app_id}")
            print(f"API Key: {api_key}")
            print(f"\nThis key has been saved and will be used as default in the test UI.")
        except Exception as e:
            print(f"Error creating test API key: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

