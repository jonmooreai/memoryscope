"""
MemoryScope v2 Reconstruction Engine

Reconstructs context from impacts and seeds (PRD v2.2 Section 5.3).

Key requirements:
- Returns reconstructed_context labeled with confidence
- Includes sources (impacts, seeds), events excluded unless explicitly allowed
- Obeys safety and access modes
- NEVER regenerates sealed narrative (hard requirement)
"""
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from app.memoryscope.core_types import (
    MemoryObject,
    MemoryType,
    MemoryState,
    PurposeType,
    Scope,
    Constraint,
    ConstraintKind,
)
from app.memoryscope.retrieval import RetrievalEngine


class ReconstructionEngine:
    """
    Reconstruction engine for context reconstruction.
    
    Reconstructs context from impacts and seeds without regenerating
    sealed narrative. This is deterministic and policy-aware.
    """
    
    def __init__(self, retrieval_engine: RetrievalEngine):
        self.retrieval_engine = retrieval_engine
    
    def reconstruct_context(
        self,
        db: Session,
        tenant_id: str,
        scope: Scope,
        purpose: PurposeType,
        query_text: Optional[str] = None,
        include_events: bool = False,
    ) -> Dict[str, Any]:
        """
        Reconstruct context from impacts and seeds.
        
        Args:
            db: Database session
            tenant_id: Tenant ID
            scope: Scope to query
            purpose: Purpose for reconstruction
            query_text: Optional query text
            include_events: Whether to include events (requires explicit consent)
        
        Returns:
            {
                "reconstructed_context": str,
                "confidence": float,
                "sources": {
                    "impacts": List[str],
                    "seeds": List[str],
                    "events": List[str],  # Only if include_events=True
                },
            }
        """
        # Retrieve memories with policy enforcement
        result = self.retrieval_engine.retrieve_for_purpose(
            db=db,
            tenant_id=tenant_id,
            scope=scope,
            purpose=purpose,
            query_text=query_text,
            limit=100,  # Get more for reconstruction
        )
        
        # Build reconstructed context from impacts
        context_parts = []
        impact_ids = []
        seed_ids = result.get("seeds", [])
        event_ids = []
        
        # Process impacts (constraints)
        if result.get("impacts"):
            constraints = result["impacts"]
            
            # Group constraints by kind
            constraints_by_kind: Dict[str, List[Dict[str, Any]]] = {}
            for constraint in constraints:
                kind = constraint.get("kind", "unknown")
                if kind not in constraints_by_kind:
                    constraints_by_kind[kind] = []
                constraints_by_kind[kind].append(constraint)
            
            # Build context from constraints
            if constraints_by_kind.get("avoid"):
                avoid_items = []
                for c in constraints_by_kind["avoid"]:
                    params = c.get("params", {})
                    if "content_class" in params:
                        avoid_items.append(params["content_class"])
                    if "phrase_ids" in params:
                        avoid_items.extend(params["phrase_ids"])
                
                if avoid_items:
                    context_parts.append(f"Avoid: {', '.join(avoid_items)}")
            
            if constraints_by_kind.get("prefer"):
                prefer_items = []
                for c in constraints_by_kind["prefer"]:
                    params = c.get("params", {})
                    if "attribute" in params and "value" in params:
                        prefer_items.append(f"{params['attribute']}={params['value']}")
                
                if prefer_items:
                    context_parts.append(f"Prefer: {', '.join(prefer_items)}")
            
            if constraints_by_kind.get("require"):
                require_items = []
                for c in constraints_by_kind["require"]:
                    params = c.get("params", {})
                    if "behavior" in params:
                        require_items.append(params["behavior"])
                
                if require_items:
                    context_parts.append(f"Require: {', '.join(require_items)}")
            
            if constraints_by_kind.get("tone"):
                tone_items = []
                for c in constraints_by_kind["tone"]:
                    params = c.get("params", {})
                    if "tone_profile" in params:
                        tone_items.append(params["tone_profile"])
                
                if tone_items:
                    context_parts.append(f"Tone: {', '.join(tone_items)}")
            
            if constraints_by_kind.get("style"):
                style_items = []
                for c in constraints_by_kind["style"]:
                    params = c.get("params", {})
                    if "format" in params:
                        style_items.append(params["format"])
                
                if style_items:
                    context_parts.append(f"Style: {', '.join(style_items)}")
            
            if constraints_by_kind.get("boundary"):
                boundary_items = []
                for c in constraints_by_kind["boundary"]:
                    params = c.get("params", {})
                    if "boundary_type" in params:
                        boundary_items.append(params["boundary_type"])
                
                if boundary_items:
                    context_parts.append(f"Boundaries: {', '.join(boundary_items)}")
            
            if constraints_by_kind.get("safety"):
                safety_items = []
                for c in constraints_by_kind["safety"]:
                    params = c.get("params", {})
                    if "mode" in params:
                        safety_items.append(params["mode"])
                
                if safety_items:
                    context_parts.append(f"Safety: {', '.join(safety_items)}")
            
            # Collect impact source IDs
            for constraint in constraints:
                source_refs = constraint.get("source_refs", [])
                impact_ids.extend(source_refs)
        
        # Process seeds (cues)
        if seed_ids:
            seed_cues = []
            for seed in seed_ids:
                if isinstance(seed, dict):
                    cues = seed.get("cues", [])
                    seed_cues.extend(cues)
            
            if seed_cues:
                context_parts.append(f"Associative cues: {', '.join(seed_cues[:10])}")  # Limit to 10
        
        # Include events only if explicitly allowed
        if include_events:
            # Get event memories (non-sealed only)
            event_memories = [
                mid for mid in result.get("events", [])
                if mid not in result.get("denied_ids", [])
            ]
            event_ids = event_memories[:5]  # Limit to 5 events
            
            # Note: We do NOT include event content/narrative
            # Only reference that events exist
            if event_ids:
                context_parts.append(f"Referenced events: {len(event_ids)} (content not included)")
        else:
            # Events are excluded by default
            context_parts.append("Events: excluded (sealed memories not reconstructed)")
        
        # Build final context
        if context_parts:
            reconstructed_context = "\n".join(context_parts)
        else:
            reconstructed_context = "No relevant context found."
        
        # Calculate confidence
        # Confidence based on number of sources and their strength
        confidence = 0.0
        if impact_ids:
            confidence += 0.4  # Impacts are strong signals
        if seed_ids:
            confidence += 0.2  # Seeds are weaker signals
        if include_events and event_ids:
            confidence += 0.1  # Events add some confidence
        confidence = min(1.0, confidence)
        
        # If we have constraints, increase confidence
        if result.get("impacts"):
            confidence = max(confidence, 0.5)  # At least 0.5 if we have impacts
        
        return {
            "reconstructed_context": reconstructed_context,
            "confidence": confidence,
            "sources": {
                "impacts": list(set(impact_ids)),  # Dedupe
                "seeds": [s.get("id") if isinstance(s, dict) else s for s in seed_ids],
                "events": event_ids,
            },
        }

