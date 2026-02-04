"""
MemoryScope v2 Retrieval Engine

Implements policy-aware memory retrieval with sealed memory filtering
and truth mode enforcement (PRD v2.2 Section 5).
"""
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from app.memoryscope.core_types import (
    MemoryObject,
    MemoryType,
    TruthMode,
    MemoryState,
    PurposeType,
    Scope,
    Constraint,
)
from app.memoryscope.policy_engine import PolicyEngine
from app.memoryscope.storage import query_memories, get_memory


class RetrievalEngine:
    """
    Retrieval engine with policy enforcement.
    
    Features:
    - Sealed memory filtering (never returned for chat_response)
    - Truth mode enforcement (counterfactual/imagined blocked for tool_execution)
    - Disputed facts suppression
    - Impact and seed extraction
    """
    
    def __init__(self, policy_engine: PolicyEngine):
        self.policy_engine = policy_engine
    
    def retrieve_for_purpose(
        self,
        db: Session,
        tenant_id: str,
        scope: Scope,
        purpose: PurposeType,
        query_text: Optional[str] = None,
        limit: int = 50,
    ) -> Dict[str, Any]:
        """
        Retrieve memories for a specific purpose with policy enforcement.
        
        Returns:
            {
                "memory_ids": List[str],
                "impacts": List[Dict],  # Constraint objects
                "seeds": List[Dict],
                "events": List[str],  # Only non-sealed events
                "denied_ids": List[str],
            }
        """
        # Build filters based on purpose
        filters = {}
        
        # For chat_response: exclude sealed events
        if purpose == PurposeType.CHAT_RESPONSE:
            filters["exclude_sealed"] = True
            filters["exclude_disputed"] = True
        
        # For task_execution: exclude nonfactual truth modes
        if purpose == PurposeType.TASK_EXECUTION:
            filters["exclude_sealed"] = True
            filters["exclude_disputed"] = True
            # Will filter truth modes in policy evaluation
        
        # Query memories (with optional text search)
        all_memories = query_memories(
            db=db,
            tenant_id=tenant_id,
            scope=scope,
            filters=filters,
            limit=limit * 2,  # Get more, then filter
            query_text=query_text,  # Pass query text for text-based filtering
        )
        
        # Apply policy evaluation to each memory
        allowed_memories = []
        denied_ids = []
        impacts = []
        seeds = []
        events = []
        
        for memory in all_memories:
            # Evaluate policy
            policy_result = self.policy_engine.evaluate_query(
                memory=memory,
                purpose=purpose,
            )
            
            if not policy_result["allowed"]:
                denied_ids.append(memory.id)
                continue
            
            allowed_memories.append(memory)
            
            # Categorize by type
            if memory.type == MemoryType.IMPACT:
                # Extract constraints from impact payload
                if memory.impact_payload and memory.impact_payload.constraints:
                    impacts.extend(memory.impact_payload.constraints)
            elif memory.type == MemoryType.SEED:
                seeds.append({
                    "id": memory.id,
                    "cues": memory.seed_payload.cues if memory.seed_payload else [],
                })
            elif memory.type == MemoryType.EVENT:
                # Only include non-sealed events
                if memory.state != MemoryState.SEALED:
                    events.append(memory.id)
        
        # Additional filtering for task_execution: remove nonfactual
        if purpose == PurposeType.TASK_EXECUTION:
            task_allowed = []
            for memory in allowed_memories:
                if memory.truth_mode in [TruthMode.COUNTERFACTUAL, TruthMode.IMAGINED, TruthMode.SOCIALLY_SOURCED]:
                    denied_ids.append(memory.id)
                else:
                    task_allowed.append(memory)
            allowed_memories = task_allowed
        
        return {
            "memory_ids": [m.id for m in allowed_memories],
            "impacts": impacts,
            "seeds": seeds,
            "events": events,
            "denied_ids": denied_ids,
        }
    
    def get_memory_by_id(
        self,
        db: Session,
        memory_id: str,
        tenant_id: str,
    ) -> Optional[MemoryObject]:
        """Get a single memory by ID."""
        return get_memory(db, memory_id, tenant_id)

