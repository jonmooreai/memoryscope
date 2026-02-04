"""
MemoryScope Core API v2 Endpoints
PRD v2.2 Implementation

Main API router for v2 endpoints.
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from uuid import uuid4
import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

from app.database import get_db, get_default_app
from app.models import App
from app.schemas_v2 import (
    MemoryCreateRequestV2,
    MemoryCreateResponseV2,
    MemoryQueryRequestV2,
    MemoryQueryResponseV2,
    ReconstructRequestV2,
    ReconstructResponseV2,
    SealMemoryRequestV2,
    SealMemoryResponseV2,
    RevokeMemoryRequestV2,
    RevokeMemoryResponseV2,
    ReinforceMemoryRequestV2,
    ReinforceMemoryResponseV2,
    RecallMemoryRequestV2,
    RecallMemoryResponseV2,
    DisputeMemoryRequestV2,
    DisputeMemoryResponseV2,
    AttestMemoryRequestV2,
    AttestMemoryResponseV2,
    BridgeScopeRequestV2,
    BridgeScopeResponseV2,
    ExplainRequestV2,
    ExplainResponseV2,
    ReplayRequestV2,
    ReplayResponseV2,
)
from app.memoryscope.core_types import (
    MemoryObject,
    MemoryType,
    TruthMode,
    MemoryState,
    Scope,
    PurposeType,
    generate_memory_id,
    generate_log_id,
    AccessLogEntry,
    Caller,
    Query,
    Decision,
)
from app.memoryscope.policy_engine import PolicyEngine
from app.memoryscope.storage import (
    store_memory,
    get_memory,
    update_memory_state,
    reinforce_memory,
    store_access_log,
)
from app.memoryscope.retrieval import RetrievalEngine
from app.memoryscope.reconstruction import ReconstructionEngine
from app.memoryscope.impact_extraction import ImpactExtractor, extract_and_store_impact
from app.memoryscope.observability import ObservabilityEngine

router = APIRouter(prefix="/v2", tags=["v2"])


def _get_app(db: Session = Depends(get_db)) -> App:
    """Dependency: default app (core API, no API keys)."""
    return get_default_app(db)


# Global policy engine (will be configurable later)
_policy_engine: Optional[PolicyEngine] = None
_retrieval_engine: Optional[RetrievalEngine] = None
_reconstruction_engine: Optional[ReconstructionEngine] = None
_observability_engine: Optional[ObservabilityEngine] = None


def get_policy_engine() -> PolicyEngine:
    """Get or create policy engine."""
    global _policy_engine
    if _policy_engine is None:
        _policy_engine = PolicyEngine()
    return _policy_engine


def get_retrieval_engine() -> RetrievalEngine:
    """Get or create retrieval engine."""
    global _retrieval_engine
    if _retrieval_engine is None:
        _retrieval_engine = RetrievalEngine(get_policy_engine())
    return _retrieval_engine


def get_reconstruction_engine() -> ReconstructionEngine:
    """Get or create reconstruction engine."""
    global _reconstruction_engine
    if _reconstruction_engine is None:
        _reconstruction_engine = ReconstructionEngine(get_retrieval_engine())
    return _reconstruction_engine


def get_observability_engine() -> ObservabilityEngine:
    """Get or create observability engine."""
    global _observability_engine
    if _observability_engine is None:
        _observability_engine = ObservabilityEngine()
    return _observability_engine


# ============================================================================
# Memory Endpoints
# ============================================================================

@router.post(
    "/memories",
    response_model=MemoryCreateResponseV2,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new memory (v2)",
    description="""
    Create a new memory following MemoryScope Core API v2.2 specification.
    
    Features:
    - Automatic classification of type, truth_mode, sensitivity
    - Policy-driven state assignment (e.g., sealed for sensitive events)
    - Automatic impact/seed derivation if policy allows
    - Full policy trace
    """,
)
def create_memory_v2(
    request: Request,
    memory_request: MemoryCreateRequestV2,
    app: App = Depends(_get_app),
    db: Session = Depends(get_db),
):
    """Create a new memory (v2)."""
    try:
        policy_engine = get_policy_engine()
        
        # Build MemoryObject from request
        # Note: This is a simplified version - full implementation would validate all fields
        memory_id = generate_memory_id()
        
        # Parse nested models from dicts
        from app.memoryscope.core_types import (
            Sensitivity, Ownership, Temporal, Content, Affect,
            ImpactPayload, SeedPayload, ProceduralPayload, SomaticPayload,
            Strength, Provenance, SourceType, SurfaceType,
            ReconsolidationPolicy,
        )
        
        # Create MemoryObject with proper nested models
        memory = MemoryObject(
            id=memory_id,
            tenant_id=memory_request.tenant_id,
            scope=Scope(**memory_request.scope),
            type=memory_request.type,
            truth_mode=memory_request.truth_mode,
            state=memory_request.state or MemoryState.ACTIVE,
            sensitivity=Sensitivity(**(memory_request.sensitivity or {"level": "low", "categories": [], "handling": "normal"})),
            ownership=Ownership(**memory_request.ownership),
            temporal=Temporal(**memory_request.temporal),
            content=Content(**memory_request.content),
            affect=Affect(**(memory_request.affect or {})),
            impact_payload=ImpactPayload(**(memory_request.impact_payload or {})) if memory_request.impact_payload else None,
            seed_payload=SeedPayload(**(memory_request.seed_payload or {})) if memory_request.seed_payload else None,
            procedural_payload=ProceduralPayload(**(memory_request.procedural_payload or {})) if memory_request.procedural_payload else None,
            somatic_payload=SomaticPayload(**(memory_request.somatic_payload or {})) if memory_request.somatic_payload else None,
            strength=Strength(**(memory_request.strength or {
                "current": 0.75,
                "initial": 0.75,
                "decay_model": "half_life"
            })),
            provenance=Provenance(**memory_request.provenance),
            reconsolidation_policy=ReconsolidationPolicy(memory_request.reconsolidation_policy) if memory_request.reconsolidation_policy else ReconsolidationPolicy.NEVER_EDIT_SOURCE,
        )
        
        # Evaluate policy for ingest
        policy_result = policy_engine.evaluate_ingest(memory)
        
        # Apply policy decisions
        memory.state = policy_result["state"]
        
        # Store memory in database
        store_memory(db, memory, str(app.id))
        
        # Derive impacts if policy allows
        if policy_result["derive_impacts"] and memory.type == MemoryType.EVENT:
            extractor = ImpactExtractor()
            extract_and_store_impact(
                db=db,
                event=memory,
                app_id=str(app.id),
                extractor=extractor,
                policy_allows=True,
            )
        
        # TODO: Derive seeds if policy allows
        # if policy_result["derive_seeds"]:
        #     derive_seeds(memory)
    
        return MemoryCreateResponseV2(
            id=memory.id,
            tenant_id=memory.tenant_id,
            state=memory.state,
            created_at=datetime.utcnow(),
            policy_trace=policy_result["trace"].model_dump() if hasattr(policy_result["trace"], "model_dump") else {},
        )
    except Exception as e:
        import traceback
        logger.error(f"Error in create_memory_v2: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to create memory: {str(e)}"
        )


@router.post(
    "/memories/query",
    response_model=MemoryQueryResponseV2,
    summary="Query memories (v2)",
    description="""
    Query memories with policy enforcement.
    
    Features:
    - Sealed memories never returned for chat_response
    - Truth mode enforcement (counterfactual/imagined never for tool_execution)
    - Disputed facts suppressed
    - Full policy trace
    """,
)
def query_memories_v2(
    request: Request,
    query_request: MemoryQueryRequestV2,
    app: App = Depends(_get_app),
    db: Session = Depends(get_db),
):
    """Query memories with policy enforcement (v2)."""
    try:
        retrieval_engine = get_retrieval_engine()
        policy_engine = get_policy_engine()
        
        # Retrieve memories with policy enforcement
        scope = Scope(**query_request.scope)
        result = retrieval_engine.retrieve_for_purpose(
            db=db,
            tenant_id=query_request.tenant_id,
            scope=scope,
            purpose=query_request.purpose,
            query_text=query_request.query_text,
            limit=query_request.limit,
        )
    except Exception as e:
        import traceback
        logger.error(f"Error in query_memories_v2: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")
    
    # Create access log entry
    log_id = generate_log_id()
    access_log = AccessLogEntry(
        log_id=log_id,
        time=datetime.utcnow(),
        tenant_id=query_request.tenant_id,
        caller=Caller(
            client_id=str(app.id),
            user_id=None,  # TODO: Extract from auth
            ip=request.client.host if request.client else None,
        ),
        scope=scope,
        purpose=query_request.purpose,
        query=Query(
            text=query_request.query_text,
            op="query",
        ),
        decision=Decision(
            allowed=True,
            returned_ids=result["memory_ids"],
            denied_ids=result["denied_ids"],
            matched_rules=[],
            explanation=f"Retrieved {len(result['memory_ids'])} memories, denied {len(result['denied_ids'])}",
        ),
    )
    
    # Store access log
    try:
        store_access_log(db, access_log)
    except Exception as e:
        logger.warning(f"Failed to store access log: {str(e)}")
        # Continue without access log
    
    return MemoryQueryResponseV2(
        memory_ids=result["memory_ids"],
        impacts=result["impacts"],
        seeds=result["seeds"],
        events=result["events"],
        denied_ids=result["denied_ids"],
        policy_trace={},  # TODO: Aggregate policy traces
        access_log_id=log_id,
    )


@router.post(
    "/reconstruct",
    response_model=ReconstructResponseV2,
    summary="Reconstruct context (v2)",
    description="""
    Reconstruct context from impacts and seeds.
    
    Features:
    - Never regenerates sealed narrative
    - Returns reconstructed_context with confidence
    - Includes sources (impacts, seeds, optionally events)
    - Obeys safety and access modes
    """,
)
def reconstruct_v2(
    request: Request,
    reconstruct_request: ReconstructRequestV2,
    app: App = Depends(_get_app),
    db: Session = Depends(get_db),
):
    """Reconstruct context from memories (v2)."""
    reconstruction_engine = get_reconstruction_engine()
    
    # Reconstruct context
    scope = Scope(**reconstruct_request.scope)
    result = reconstruction_engine.reconstruct_context(
        db=db,
        tenant_id=reconstruct_request.tenant_id,
        scope=scope,
        purpose=reconstruct_request.purpose,
        query_text=reconstruct_request.query_text,
        include_events=reconstruct_request.include_events,
    )
    
    # Create access log entry
    log_id = generate_log_id()
    access_log = AccessLogEntry(
        log_id=log_id,
        time=datetime.utcnow(),
        tenant_id=reconstruct_request.tenant_id,
        caller=Caller(
            client_id=str(app.id),
            user_id=None,  # TODO: Extract from auth
            ip=request.client.host if request.client else None,
        ),
        scope=scope,
        purpose=reconstruct_request.purpose,
        query=Query(
            text=reconstruct_request.query_text,
            op="reconstruct",
        ),
        decision=Decision(
            allowed=True,
            returned_ids=result["sources"]["impacts"] + result["sources"]["seeds"] + result["sources"]["events"],
            denied_ids=[],
            matched_rules=[],
            explanation=f"Reconstructed context with confidence {result['confidence']:.2f}",
        ),
    )
    
    # Store access log
    store_access_log(db, access_log)
    
    return ReconstructResponseV2(
        reconstructed_context=result["reconstructed_context"],
        confidence=result["confidence"],
        sources=result["sources"],
        policy_trace={},  # TODO: Aggregate policy traces
        access_log_id=log_id,
    )


# ============================================================================
# Memory Operations
# ============================================================================

@router.post(
    "/memories/{memory_id}/seal",
    response_model=SealMemoryResponseV2,
    summary="Seal a memory",
)
def seal_memory_v2(
    memory_id: str,
    seal_request: SealMemoryRequestV2,
    app: App = Depends(_get_app),
    db: Session = Depends(get_db),
):
    """Seal a memory."""
    memory = update_memory_state(
        db=db,
        memory_id=memory_id,
        tenant_id=seal_request.tenant_id,
        new_state=MemoryState.SEALED,
    )
    
    if memory is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Memory not found",
        )
    
    return SealMemoryResponseV2(
        id=memory.id,
        state=memory.state,
        sealed_at=datetime.utcnow(),
    )


@router.post(
    "/memories/{memory_id}/revoke",
    response_model=RevokeMemoryResponseV2,
    summary="Revoke a memory",
)
def revoke_memory_v2(
    memory_id: str,
    revoke_request: RevokeMemoryRequestV2,
    app: App = Depends(_get_app),
    db: Session = Depends(get_db),
):
    """Revoke a memory."""
    # TODO: Implement revocation with propagation
    return RevokeMemoryResponseV2(
        id=memory_id,
        state=MemoryState.REVOKED,
        revoked_at=datetime.utcnow(),
        propagated_to=[],
    )


@router.post(
    "/memories/{memory_id}/reinforce",
    response_model=ReinforceMemoryResponseV2,
    summary="Reinforce a memory",
)
def reinforce_memory_v2(
    memory_id: str,
    reinforce_request: ReinforceMemoryRequestV2,
    app: App = Depends(_get_app),
    db: Session = Depends(get_db),
):
    """Reinforce a memory (increase strength)."""
    memory = reinforce_memory(
        db=db,
        memory_id=memory_id,
        tenant_id=reinforce_request.tenant_id,
        strength_delta=reinforce_request.strength_delta,
    )
    
    if memory is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Memory not found",
        )
    
    return ReinforceMemoryResponseV2(
        id=memory.id,
        strength={
            "current": float(memory.strength.current),
            "initial": float(memory.strength.initial),
        },
        reinforced_at=datetime.utcnow(),
    )


@router.post(
    "/memories/{memory_id}/recall",
    response_model=RecallMemoryResponseV2,
    summary="Recall (reconsolidate) a memory",
)
def recall_memory_v2(
    memory_id: str,
    recall_request: RecallMemoryRequestV2,
    app: App = Depends(_get_app),
    db: Session = Depends(get_db),
):
    """Recall (reconsolidate) a memory."""
    # TODO: Implement recall with reconsolidation rules
    return RecallMemoryResponseV2(
        id=memory_id,
        updated_at=datetime.utcnow(),
        reconsolidation_trace=[],
    )


# ============================================================================
# Governance
# ============================================================================

@router.post(
    "/memories/{memory_id}/dispute",
    response_model=DisputeMemoryResponseV2,
    summary="Dispute a memory",
)
def dispute_memory_v2(
    memory_id: str,
    dispute_request: DisputeMemoryRequestV2,
    app: App = Depends(_get_app),
    db: Session = Depends(get_db),
):
    """Dispute a memory."""
    # TODO: Implement dispute handling
    return DisputeMemoryResponseV2(
        id=memory_id,
        dispute_state=dispute_request.new_dispute_state,
        disputed_at=datetime.utcnow(),
    )


@router.post(
    "/memories/{memory_id}/attest",
    response_model=AttestMemoryResponseV2,
    summary="Attest to a memory",
)
def attest_memory_v2(
    memory_id: str,
    attest_request: AttestMemoryRequestV2,
    app: App = Depends(_get_app),
    db: Session = Depends(get_db),
):
    """Attest to a memory."""
    # TODO: Implement attestation
    return AttestMemoryResponseV2(
        id=memory_id,
        dispute_state=DisputeState.UNDISPUTED,
        attested_at=datetime.utcnow(),
    )


@router.post(
    "/scopes/{scope_id}/bridge",
    response_model=BridgeScopeResponseV2,
    summary="Bridge scopes",
)
def bridge_scope_v2(
    scope_id: str,
    bridge_request: BridgeScopeRequestV2,
    app: App = Depends(_get_app),
    db: Session = Depends(get_db),
):
    """Bridge scopes (share memories between scopes)."""
    # TODO: Implement scope bridging
    return BridgeScopeResponseV2(
        bridged_memory_ids=[],
        bridged_at=datetime.utcnow(),
    )


# ============================================================================
# Observability
# ============================================================================

@router.post(
    "/explain",
    response_model=ExplainResponseV2,
    summary="Explain a decision",
)
def explain_v2(
    request: Request,
    explain_request: ExplainRequestV2,
    app: App = Depends(_get_app),
    db: Session = Depends(get_db),
):
    """Explain a decision (internal, trusted callers)."""
    observability_engine = get_observability_engine()
    
    result = observability_engine.explain_decision(
        db=db,
        tenant_id=explain_request.tenant_id,
        access_log_id=explain_request.access_log_id,
        memory_ids=explain_request.memory_ids,
        request_context=explain_request.request_context,
    )
    
    return ExplainResponseV2(
        explanation=result["explanation"],
        memory_ids_used=result["memory_ids_used"],
        constraints_applied=result["constraints_applied"],
        denials=result["denials"],
        spiral_state=result["spiral_state"],
        tool_gate_decision=result["tool_gate_decision"],
        reinforcement_blocked=result["reinforcement_blocked"],
    )


@router.post(
    "/replay",
    response_model=ReplayResponseV2,
    summary="Replay a request",
)
def replay_v2(
    request: Request,
    replay_request: ReplayRequestV2,
    app: App = Depends(_get_app),
    db: Session = Depends(get_db),
):
    """Replay a request for debugging."""
    observability_engine = get_observability_engine()
    
    result = observability_engine.replay_request(
        db=db,
        tenant_id=replay_request.tenant_id,
        access_log_id=replay_request.access_log_id,
        override_context=replay_request.override_context,
    )
    
    return ReplayResponseV2(
        result=result["result"],
        policy_trace=result["policy_trace"],
        access_log_id=replay_request.access_log_id,
    )

