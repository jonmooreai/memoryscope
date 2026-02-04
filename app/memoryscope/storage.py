"""
MemoryScope v2 Storage Utilities

Converts between MemoryObject (Pydantic) and database models.
Handles serialization, indexing, and retrieval.
"""
from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.models import MemoryV2, MemoryLinkV2, AccessLogV2, SpiralArtifactV2
from app.memoryscope.core_types import (
    MemoryObject,
    MemoryType,
    TruthMode,
    MemoryState,
    Scope,
    PurposeType,
    AccessLogEntry,
    ThoughtPatternArtifact,
    DerivedObjectLink,
    DisputeState,
)


def memory_object_to_db(memory: MemoryObject, app_id: str) -> MemoryV2:
    """
    Convert MemoryObject to database model.
    
    Extracts indexed fields for efficient querying while storing
    complete object as JSONB.
    """
    return MemoryV2(
        id=memory.id,
        tenant_id=memory.tenant_id,
        scope_type=memory.scope.scope_type.value,
        scope_id=memory.scope.scope_id,
        type=memory.type.value,
        truth_mode=memory.truth_mode.value,
        state=memory.state.value,
        sensitivity_level=memory.sensitivity.level.value,
        sensitivity_categories=memory.sensitivity.categories,
        dispute_state=memory.ownership.dispute_state.value,
        occurred_at_observed=memory.temporal.occurred_at_observed,
        occurred_at_claimed=memory.temporal.occurred_at_claimed,
        strength_current=memory.strength.current,
        last_reinforced_at=memory.strength.last_reinforced_at,
        memory_object_json=memory.model_dump(mode="json"),
        app_id=app_id,
    )


def db_to_memory_object(db_memory: MemoryV2) -> MemoryObject:
    """Convert database model to MemoryObject."""
    return MemoryObject(**db_memory.memory_object_json)


def store_memory(db: Session, memory: MemoryObject, app_id: str) -> MemoryV2:
    """Store a memory in the database."""
    db_memory = memory_object_to_db(memory, app_id)
    db.add(db_memory)
    db.commit()
    db.refresh(db_memory)
    return db_memory


def get_memory(db: Session, memory_id: str, tenant_id: str) -> Optional[MemoryObject]:
    """Get a memory by ID."""
    db_memory = db.query(MemoryV2).filter(
        and_(
            MemoryV2.id == memory_id,
            MemoryV2.tenant_id == tenant_id,
        )
    ).first()
    
    if db_memory is None:
        return None
    
    return db_to_memory_object(db_memory)


def query_memories(
    db: Session,
    tenant_id: str,
    scope: Scope,
    filters: Optional[Dict[str, Any]] = None,
    limit: int = 50,
    query_text: Optional[str] = None,
) -> List[MemoryObject]:
    """
    Query memories with policy-aware filtering.
    
    Filters:
    - state: List of states to include
    - type: List of types to include
    - truth_mode: List of truth modes to include
    - exclude_sealed: Boolean to exclude sealed memories
    - exclude_disputed: Boolean to exclude disputed memories
    - min_strength: Minimum strength threshold
    
    query_text: Optional text to search for in memory content (searches JSONB content field)
    """
    import logging
    from sqlalchemy import func, or_
    logger = logging.getLogger(__name__)
    
    try:
        query = db.query(MemoryV2).filter(
            and_(
                MemoryV2.tenant_id == tenant_id,
                MemoryV2.scope_type == scope.scope_type.value,
                MemoryV2.scope_id == scope.scope_id,
            )
        )
        
        if filters:
            if "state" in filters:
                states = [s.value if isinstance(s, MemoryState) else s for s in filters["state"]]
                query = query.filter(MemoryV2.state.in_(states))
            
            if "type" in filters:
                types = [t.value if isinstance(t, MemoryType) else t for t in filters["type"]]
                query = query.filter(MemoryV2.type.in_(types))
            
            if "truth_mode" in filters:
                truth_modes = [tm.value if isinstance(tm, TruthMode) else tm for tm in filters["truth_mode"]]
                query = query.filter(MemoryV2.truth_mode.in_(truth_modes))
            
            if filters.get("exclude_sealed", False):
                query = query.filter(MemoryV2.state != MemoryState.SEALED.value)
            
            if filters.get("exclude_disputed", False):
                query = query.filter(
                    ~MemoryV2.dispute_state.in_([DisputeState.DISPUTED.value, DisputeState.CONTESTED.value])
                )
            
            if "min_strength" in filters:
                query = query.filter(MemoryV2.strength_current >= filters["min_strength"])
        
        # Text-based search in JSONB content field
        if query_text:
            search_terms = query_text.lower().split()
            # Search in the content.text field within the JSONB
            # PostgreSQL JSONB: memory_object_json->'content'->>'text'
            conditions = []
            for term in search_terms:
                if len(term) > 2:  # Only search terms longer than 2 characters
                    # Use PostgreSQL JSONB text extraction and ILIKE for case-insensitive search
                    # Extract text from JSONB path: memory_object_json->'content'->>'text'
                    text_field = MemoryV2.memory_object_json['content']['text'].astext
                    conditions.append(text_field.ilike(f'%{term}%'))
            if conditions:
                query = query.filter(or_(*conditions))
        
        # Order by occurred_at_observed descending (most recent first)
        # If query_text provided, prioritize by relevance (simplified: just by recency for now)
        query = query.order_by(MemoryV2.occurred_at_observed.desc())
        
        # Limit results
        db_memories = query.limit(limit).all()
        
        return [db_to_memory_object(m) for m in db_memories]
    except Exception as e:
        logger.error(f"Error querying memories: {str(e)}", exc_info=True)
        # Return empty list on error rather than crashing
        return []


def update_memory_state(
    db: Session,
    memory_id: str,
    tenant_id: str,
    new_state: MemoryState,
) -> Optional[MemoryObject]:
    """Update memory state."""
    db_memory = db.query(MemoryV2).filter(
        and_(
            MemoryV2.id == memory_id,
            MemoryV2.tenant_id == tenant_id,
        )
    ).first()
    
    if db_memory is None:
        return None
    
    # Update state in both indexed field and JSON
    db_memory.state = new_state.value
    memory_obj = db_to_memory_object(db_memory)
    memory_obj.state = new_state
    db_memory.memory_object_json = memory_obj.model_dump(mode="json")
    db_memory.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(db_memory)
    
    return db_to_memory_object(db_memory)


def reinforce_memory(
    db: Session,
    memory_id: str,
    tenant_id: str,
    strength_delta: float = 0.1,
) -> Optional[MemoryObject]:
    """Reinforce a memory (increase strength)."""
    db_memory = db.query(MemoryV2).filter(
        and_(
            MemoryV2.id == memory_id,
            MemoryV2.tenant_id == tenant_id,
        )
    ).first()
    
    if db_memory is None:
        return None
    
    memory_obj = db_to_memory_object(db_memory)
    
    # Increase strength (capped at 1.0)
    new_strength = min(1.0, memory_obj.strength.current + strength_delta)
    memory_obj.strength.current = new_strength
    memory_obj.strength.last_reinforced_at = datetime.utcnow()
    
    # Update database
    db_memory.strength_current = new_strength
    db_memory.last_reinforced_at = datetime.utcnow()
    db_memory.memory_object_json = memory_obj.model_dump(mode="json")
    db_memory.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(db_memory)
    
    return db_to_memory_object(db_memory)


def store_access_log(db: Session, access_log: AccessLogEntry) -> AccessLogV2:
    """Store an access log entry."""
    db_log = AccessLogV2(
        log_id=access_log.log_id,
        time=access_log.time,
        tenant_id=access_log.tenant_id,
        caller_client_id=access_log.caller.client_id,
        caller_user_id=access_log.caller.user_id,
        caller_ip=access_log.caller.ip,
        scope_type=access_log.scope.scope_type.value,
        scope_id=access_log.scope.scope_id,
        purpose=access_log.purpose.value,
        query_text=access_log.query.text if access_log.query else None,
        query_op=access_log.query.op if access_log.query else None,
        decision_allowed=access_log.decision.allowed,
        decision_returned_ids=access_log.decision.returned_ids,
        decision_denied_ids=access_log.decision.denied_ids,
        decision_matched_rules=access_log.decision.matched_rules,
        decision_explanation=access_log.decision.explanation,
        access_log_json=access_log.model_dump(mode="json"),
    )
    
    db.add(db_log)
    db.commit()
    db.refresh(db_log)
    return db_log


def store_memory_link(
    db: Session,
    link: DerivedObjectLink,
) -> MemoryLinkV2:
    """Store a memory link."""
    db_link = MemoryLinkV2(
        parent_id=link.parent_id,
        child_id=link.child_id,
        relationship=link.relationship,
        rule=link.rule,
        strength_transfer=link.strength_transfer,
        created_at=link.created_at,
    )
    
    db.add(db_link)
    db.commit()
    db.refresh(db_link)
    return db_link

