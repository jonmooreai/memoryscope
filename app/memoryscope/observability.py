"""
MemoryScope v2 Observability

Explain and replay functionality (PRD v2.2 Section 11).
"""
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from datetime import datetime

from app.memoryscope.core_types import (
    Scope,
    PurposeType,
)
from app.memoryscope.storage import get_memory
from app.models import AccessLogV2, MemoryV2


class ObservabilityEngine:
    """
    Observability engine for explain and replay.
    
    Provides explain packs and replay functionality for debugging
    and understanding system decisions.
    """
    
    def explain_decision(
        self,
        db: Session,
        tenant_id: str,
        access_log_id: Optional[str] = None,
        memory_ids: Optional[List[str]] = None,
        request_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Generate explain pack for a decision.
        
        Returns:
            {
                "explanation": Dict,
                "memory_ids_used": List[str],
                "constraints_applied": List[Dict],
                "denials": List[Dict],
                "spiral_state": Optional[Dict],
                "tool_gate_decision": Optional[Dict],
                "reinforcement_blocked": Optional[str],
            }
        """
        explanation = {
            "access_log_id": access_log_id,
            "memory_ids": memory_ids or [],
            "request_context": request_context or {},
        }
        
        memory_ids_used = []
        constraints_applied = []
        denials = []
        
        # If access log ID provided, get details
        if access_log_id:
            access_log = db.query(AccessLogV2).filter(
                AccessLogV2.log_id == access_log_id
            ).first()
            
            if access_log:
                explanation["access_log"] = {
                    "log_id": access_log.log_id,
                    "time": access_log.time.isoformat(),
                    "purpose": access_log.purpose,
                    "decision_allowed": access_log.decision_allowed,
                    "decision_explanation": access_log.decision_explanation,
                }
                
                memory_ids_used = access_log.decision_returned_ids or []
                denials = [
                    {
                        "memory_id": mid,
                        "reason": "Policy denied",
                    }
                    for mid in (access_log.decision_denied_ids or [])
                ]
        
        # If memory IDs provided, get memory details
        if memory_ids:
            for memory_id in memory_ids:
                memory = get_memory(db, memory_id, tenant_id)
                if memory:
                    memory_ids_used.append(memory_id)
                    
                    # Extract constraints if impact
                    if memory.type.value == "impact" and memory.impact_payload:
                        for constraint in memory.impact_payload.constraints:
                            constraints_applied.append({
                                "constraint_id": constraint.get("constraint_id"),
                                "kind": constraint.get("kind"),
                                "params": constraint.get("params"),
                                "source_memory": memory_id,
                            })
        
        return {
            "explanation": explanation,
            "memory_ids_used": list(set(memory_ids_used)),
            "constraints_applied": constraints_applied,
            "denials": denials,
            "spiral_state": None,  # TODO: Implement spiral state
            "tool_gate_decision": None,  # TODO: Implement tool gate decision
            "reinforcement_blocked": None,  # TODO: Implement reinforcement blocking
        }
    
    def replay_request(
        self,
        db: Session,
        tenant_id: str,
        access_log_id: str,
        override_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Replay a request for debugging.
        
        Returns:
            {
                "result": Dict,
                "policy_trace": Dict,
                "access_log_id": str,
            }
        """
        # Get original access log
        access_log = db.query(AccessLogV2).filter(
            AccessLogV2.log_id == access_log_id
        ).first()
        
        if not access_log:
            return {
                "result": {"error": "Access log not found"},
                "policy_trace": {},
                "access_log_id": access_log_id,
            }
        
        # Reconstruct request context from access log
        request_context = {
            "tenant_id": tenant_id,
            "scope": {
                "scope_type": access_log.scope_type,
                "scope_id": access_log.scope_id,
            },
            "purpose": access_log.purpose,
            "query_text": access_log.query_text,
        }
        
        # Apply overrides if provided
        if override_context:
            request_context.update(override_context)
        
        # Replay the query
        from app.memoryscope.retrieval import RetrievalEngine
        from app.memoryscope.policy_engine import PolicyEngine
        
        policy_engine = PolicyEngine()
        retrieval_engine = RetrievalEngine(policy_engine)
        
        scope = Scope(
            scope_type=request_context["scope"]["scope_type"],
            scope_id=request_context["scope"]["scope_id"],
        )
        
        result = retrieval_engine.retrieve_for_purpose(
            db=db,
            tenant_id=tenant_id,
            scope=scope,
            purpose=PurposeType(request_context["purpose"]),
            query_text=request_context.get("query_text"),
        )
        
        return {
            "result": {
                "memory_ids": result["memory_ids"],
                "impacts": len(result.get("impacts", [])),
                "seeds": len(result.get("seeds", [])),
                "events": len(result.get("events", [])),
                "denied_ids": result.get("denied_ids", []),
            },
            "policy_trace": {
                "policy_version": policy_engine.get_policy_version(),
            },
            "access_log_id": access_log_id,
        }

