#!/usr/bin/env python3
"""
Simple script to view the local database contents.
"""
import sys
import os
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.models import Memory, App, ReadGrant, AuditEvent
from sqlalchemy import func


def view_database():
    """View database contents."""
    db = SessionLocal()
    try:
        print("=" * 80)
        print("Memory Scope API - Database Viewer")
        print("=" * 80)
        print()
        
        # Counts
        memory_count = db.query(Memory).count()
        app_count = db.query(App).count()
        grant_count = db.query(ReadGrant).count()
        audit_count = db.query(AuditEvent).count()
        
        print("📊 Database Statistics")
        print("-" * 80)
        print(f"  Memories:     {memory_count}")
        print(f"  Apps:         {app_count}")
        print(f"  Read Grants:  {grant_count}")
        print(f"  Audit Events: {audit_count}")
        print()
        
        # Apps
        if app_count > 0:
            print("🔑 Apps")
            print("-" * 80)
            apps = db.query(App).order_by(App.created_at.desc()).all()
            for app in apps:
                print(f"  • {app.name}")
                print(f"    ID: {app.id}")
                print(f"    User ID: {app.user_id}")
                print(f"    Created: {app.created_at}")
                print()
        
        # Recent Memories
        if memory_count > 0:
            print("💾 Recent Memories (last 10)")
            print("-" * 80)
            memories = db.query(Memory).order_by(Memory.created_at.desc()).limit(10).all()
            for mem in memories:
                print(f"  • {mem.user_id} | {mem.scope} | {mem.domain or '(no domain)'}")
                print(f"    ID: {mem.id}")
                print(f"    Shape: {mem.value_shape} | Source: {mem.source}")
                print(f"    Created: {mem.created_at} | Expires: {mem.expires_at}")
                print(f"    Value: {str(mem.value_json)[:100]}...")
                print()
        
        # Memories by scope
        if memory_count > 0:
            print("📈 Memories by Scope")
            print("-" * 80)
            scope_counts = db.query(
                Memory.scope,
                func.count(Memory.id).label('count')
            ).group_by(Memory.scope).all()
            for scope, count in scope_counts:
                print(f"  {scope}: {count}")
            print()
        
        # Memories by user
        if memory_count > 0:
            print("👥 Top Users by Memory Count")
            print("-" * 80)
            user_counts = db.query(
                Memory.user_id,
                func.count(Memory.id).label('count')
            ).group_by(Memory.user_id).order_by(func.count(Memory.id).desc()).limit(10).all()
            for user_id, count in user_counts:
                print(f"  {user_id}: {count} memories")
            print()
        
    finally:
        db.close()


if __name__ == "__main__":
    view_database()

