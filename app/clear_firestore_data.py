"""
Clear all data from Firestore collections: memories, read_grants, and audit_events.

This script deletes all documents from:
- memories
- read_grants  
- audit_events

Usage:
    python3 -m app.clear_firestore_data

Warning: This will permanently delete all data from these collections!
"""

import os
import sys
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set Firebase credentials from file if not already set
FIREBASE_JSON_FILE = "/Users/jonmoore/Downloads/scoped-memory-7c9f9-firebase-adminsdk-fbsvc-03bbb965be.json"
if not os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON") and os.path.exists(FIREBASE_JSON_FILE):
    try:
        with open(FIREBASE_JSON_FILE, 'r') as f:
            firebase_data = json.load(f)
        os.environ["FIREBASE_SERVICE_ACCOUNT_JSON"] = json.dumps(firebase_data)
        print("✅ Loaded Firebase credentials from file")
    except Exception as e:
        print(f"⚠️  Could not load Firebase credentials from file: {e}")

# Initialize Firebase before importing firestore_db
from app.firebase_auth import initialize_firebase_admin

try:
    initialize_firebase_admin()
except Exception as e:
    print(f"❌ Failed to initialize Firebase: {e}")
    print("\nPlease set FIREBASE_SERVICE_ACCOUNT_PATH or FIREBASE_SERVICE_ACCOUNT_JSON")
    sys.exit(1)

from app.firestore_db import (
    get_firestore,
    COLLECTION_MEMORIES,
    COLLECTION_READ_GRANTS,
    COLLECTION_AUDIT_EVENTS,
)

def clear_collection(collection_name: str) -> int:
    """Delete all documents from a Firestore collection."""
    db = get_firestore()
    collection_ref = db.collection(collection_name)
    
    deleted_count = 0
    batch_size = 500  # Firestore batch limit
    
    # Get all documents
    docs = collection_ref.stream()
    doc_list = list(docs)
    total_docs = len(doc_list)
    
    if total_docs == 0:
        return 0
    
    print(f"  Found {total_docs} documents in {collection_name}")
    
    # Delete in batches
    for i in range(0, total_docs, batch_size):
        batch = db.batch()
        batch_docs = doc_list[i:i + batch_size]
        
        for doc in batch_docs:
            batch.delete(doc.reference)
            deleted_count += 1
        
        batch.commit()
        print(f"    Deleted batch {i // batch_size + 1} ({deleted_count}/{total_docs})")
    
    return deleted_count

def main():
    """Clear all Firestore data."""
    print("🗑️  Clearing Firestore data...")
    print("")
    print("⚠️  WARNING: This will permanently delete all data from:")
    print("   - memories")
    print("   - read_grants")
    print("   - audit_events")
    print("")
    
    response = input("Are you sure you want to continue? (yes/no): ")
    if response.lower() != "yes":
        print("❌ Aborted.")
        return
    
    print("")
    print("Clearing collections...")
    print("")
    
    total_deleted = 0
    
    # Clear memories
    print("1. Clearing memories...")
    try:
        count = clear_collection(COLLECTION_MEMORIES)
        total_deleted += count
        print(f"   ✅ Deleted {count} memories")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    print("")
    
    # Clear read grants
    print("2. Clearing read_grants...")
    try:
        count = clear_collection(COLLECTION_READ_GRANTS)
        total_deleted += count
        print(f"   ✅ Deleted {count} read grants")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    print("")
    
    # Clear audit events
    print("3. Clearing audit_events...")
    try:
        count = clear_collection(COLLECTION_AUDIT_EVENTS)
        total_deleted += count
        print(f"   ✅ Deleted {count} audit events")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    print("")
    print(f"✅ Complete! Deleted {total_deleted} total documents")
    print("")
    print("Note: Apps and user settings were NOT deleted.")
    print("      Only memories, read grants, and audit events were cleared.")

if __name__ == "__main__":
    main()

