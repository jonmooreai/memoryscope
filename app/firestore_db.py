"""
Firestore database connection and utilities.
"""
import os
from typing import Optional, Dict, Any, List
from datetime import datetime
import uuid

try:
    import firebase_admin
    from firebase_admin import credentials, firestore
    FIREBASE_AVAILABLE = True
except ImportError:
    FIREBASE_AVAILABLE = False
    firebase_admin = None
    firestore = None


# Get Firestore client
_db = None


# Initialize Firebase Admin SDK
# Use shared initialization from firebase_auth module
def initialize_firebase():
    """Initialize Firebase Admin SDK for Firestore."""
    # Import here to avoid circular dependency
    from app.firebase_auth import initialize_firebase_admin
    
    # Initialize Firebase Admin SDK (shared with auth)
    initialize_firebase_admin()
    
    # Return Firestore client
    if not FIREBASE_AVAILABLE:
        raise ImportError("firebase-admin not installed. Run: pip install firebase-admin")
    
    # Check if already initialized
    if firebase_admin._apps:
        return firestore.client()
    
    # If initialization didn't happen, try to get client anyway
    # (might have been initialized elsewhere)
    try:
        return firestore.client()
    except Exception as e:
        raise ValueError(
            "Firebase not initialized. Set FIREBASE_SERVICE_ACCOUNT_PATH or "
            "FIREBASE_SERVICE_ACCOUNT_JSON environment variable, or use gcloud auth."
        ) from e


def get_firestore():
    """Get Firestore client instance."""
    global _db
    if _db is None:
        _db = initialize_firebase()
    return _db


# Collection names
COLLECTION_APPS = "apps"
COLLECTION_MEMORIES = "memories"
COLLECTION_READ_GRANTS = "read_grants"
COLLECTION_AUDIT_EVENTS = "audit_events"
COLLECTION_USERS = "users"


# Helper functions for Firestore operations
def timestamp_to_datetime(timestamp) -> Optional[datetime]:
    """Convert Firestore timestamp to Python datetime."""
    if timestamp is None:
        return None
    if hasattr(timestamp, "timestamp"):
        # Firestore Timestamp object
        return timestamp.to_datetime()
    if isinstance(timestamp, datetime):
        return timestamp
    if isinstance(timestamp, (int, float)):
        return datetime.fromtimestamp(timestamp)
    return timestamp


def datetime_to_timestamp(dt: Optional[datetime]):
    """Convert Python datetime to Firestore timestamp."""
    if dt is None:
        return firestore.SERVER_TIMESTAMP
    return dt


def doc_to_dict(doc) -> Optional[Dict[str, Any]]:
    """Convert Firestore document to dictionary."""
    if not doc.exists:
        return None
    
    data = doc.to_dict()
    # Convert Firestore timestamps to datetime
    for key, value in data.items():
        if hasattr(value, "to_datetime"):
            # Firestore Timestamp
            data[key] = value.to_datetime().timestamp()
        elif isinstance(value, datetime):
            data[key] = value.timestamp()
    
    # Ensure id is included
    data["id"] = doc.id
    return data


def create_app(user_id: str, name: str, api_key_hash: str) -> Dict[str, Any]:
    """Create a new app in Firestore."""
    db = get_firestore()
    # Generate UUID for consistent ID format
    app_id = str(uuid.uuid4())
    app_ref = db.collection(COLLECTION_APPS).document(app_id)
    
    app_data = {
        "id": app_id,
        "name": name,
        "api_key_hash": api_key_hash,
        "user_id": user_id,  # Link to user
        "created_at": firestore.SERVER_TIMESTAMP,
    }
    
    app_ref.set(app_data)
    # Get the document to return with server timestamp
    doc = app_ref.get()
    return doc_to_dict(doc) if doc.exists else app_data


def get_user_apps(user_id: str) -> List[Dict[str, Any]]:
    """Get all apps for a user."""
    db = get_firestore()
    apps_ref = db.collection(COLLECTION_APPS).where("user_id", "==", user_id)
    docs = apps_ref.stream()
    
    return [doc_to_dict(doc) for doc in docs if doc.exists]


def get_app_by_id(app_id: str) -> Optional[Dict[str, Any]]:
    """Get app by ID."""
    db = get_firestore()
    doc_ref = db.collection(COLLECTION_APPS).document(app_id)
    doc = doc_ref.get()
    
    return doc_to_dict(doc) if doc.exists else None


def delete_app(app_id: str) -> bool:
    """Delete an app."""
    db = get_firestore()
    app_ref = db.collection(COLLECTION_APPS).document(app_id)
    app_ref.delete()
    return True


def update_app_api_key(app_id: str, new_api_key_hash: str) -> Optional[Dict[str, Any]]:
    """Update an app's API key hash (for rotation)."""
    db = get_firestore()
    app_ref = db.collection(COLLECTION_APPS).document(app_id)
    
    # Update the API key hash
    app_ref.update({"api_key_hash": new_api_key_hash})
    
    # Return updated app data
    doc = app_ref.get()
    return doc_to_dict(doc) if doc.exists else None


def create_memory(memory_data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a memory in Firestore."""
    db = get_firestore()
    memory_ref = db.collection(COLLECTION_MEMORIES).document()
    
    memory_data["id"] = memory_ref.id
    memory_data["created_at"] = firestore.SERVER_TIMESTAMP
    
    memory_ref.set(memory_data)
    return memory_data


def get_memories_by_app(app_id: str) -> List[Dict[str, Any]]:
    """Get all memories for an app."""
    db = get_firestore()
    memories_ref = db.collection(COLLECTION_MEMORIES).where("app_id", "==", app_id)
    docs = memories_ref.stream()
    
    return [doc_to_dict(doc) for doc in docs if doc.exists]


def create_audit_event(event_data: Dict[str, Any]) -> Dict[str, Any]:
    """Create an audit event in Firestore."""
    db = get_firestore()
    event_ref = db.collection(COLLECTION_AUDIT_EVENTS).document()
    
    event_data["id"] = event_ref.id
    event_data["timestamp"] = firestore.SERVER_TIMESTAMP
    
    event_ref.set(event_data)
    return event_data


def get_audit_events(
    app_ids: List[str],
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> List[Dict[str, Any]]:
    """Get audit events for given apps within date range."""
    db = get_firestore()
    events_ref = db.collection(COLLECTION_AUDIT_EVENTS)
    
    # Filter by app_id
    if len(app_ids) == 1:
        events_ref = events_ref.where("app_id", "==", app_ids[0])
    else:
        # Firestore 'in' query limit is 10, so we need to handle multiple apps differently
        # For now, we'll get all and filter in Python (not ideal for large datasets)
        pass
    
    # Filter by date range
    if start_date:
        events_ref = events_ref.where("timestamp", ">=", start_date)
    if end_date:
        events_ref = events_ref.where("timestamp", "<=", end_date)
    
    # Order by timestamp
    events_ref = events_ref.order_by("timestamp", direction=firestore.Query.DESCENDING)
    
    docs = events_ref.stream()
    events = [doc_to_dict(doc) for doc in docs if doc.exists]
    
    # Filter by app_ids if multiple (since Firestore 'in' is limited to 10)
    if len(app_ids) > 1:
        events = [e for e in events if e.get("app_id") in app_ids]
    
    return events


def get_active_memories_count(app_ids: List[str]) -> int:
    """Get count of active (non-expired) memories."""
    db = get_firestore()
    now = datetime.utcnow()
    
    count = 0
    for app_id in app_ids:
        memories_ref = db.collection(COLLECTION_MEMORIES).where("app_id", "==", app_id)
        docs = memories_ref.stream()
        
        for doc in docs:
            data = doc_to_dict(doc)
            if data and data.get("expires_at"):
                expires_at_ts = data["expires_at"]
                # Convert timestamp to datetime if needed
                if isinstance(expires_at_ts, (int, float)):
                    expires_at = datetime.fromtimestamp(expires_at_ts)
                elif isinstance(expires_at_ts, datetime):
                    expires_at = expires_at_ts
                else:
                    continue
                
                if expires_at > now:
                    count += 1
    
    return count


def get_user_settings(user_id: str) -> Optional[Dict[str, Any]]:
    """Get user settings from Firestore."""
    db = get_firestore()
    doc_ref = db.collection(COLLECTION_USERS).document(user_id)
    doc = doc_ref.get()
    
    if doc.exists:
        return doc_to_dict(doc)
    return None


def save_user_settings(user_id: str, settings: Dict[str, Any]) -> Dict[str, Any]:
    """Save user settings to Firestore."""
    db = get_firestore()
    doc_ref = db.collection(COLLECTION_USERS).document(user_id)
    
    # Merge with existing settings if any
    existing = doc_ref.get()
    if existing.exists:
        existing_data = existing.to_dict()
        existing_data.update(settings)
        doc_ref.update(existing_data)
    else:
        doc_ref.set(settings)
    
    # Return updated settings
    doc = doc_ref.get()
    return doc_to_dict(doc) if doc.exists else settings


def get_total_memories_count(app_ids: List[str]) -> int:
    """Get total count of memories."""
    db = get_firestore()
    
    count = 0
    for app_id in app_ids:
        memories_ref = db.collection(COLLECTION_MEMORIES).where("app_id", "==", app_id)
        count += len(list(memories_ref.stream()))
    
    return count

