"""
MemoryScope Core API v2 Schemas
PRD v2.2 Implementation

Request/Response schemas for v2 API endpoints.
"""
from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import UUID
from pydantic import BaseModel, Field

from app.memoryscope.core_types import (
    MemoryObject,
    MemoryType,
    TruthMode,
    MemoryState,
    Scope,
    PurposeType,
    SensitivityLevel,
    DisputeState,
    OwnerType,
    Visibility,
    TimePrecision,
    Content,
    Affect,
    Constraint,
)


# ============================================================================
# Memory Creation (POST /v2/memories)
# ============================================================================

class MemoryCreateRequestV2(BaseModel):
    """Request to create a memory (v2)."""
    tenant_id: str = Field(..., pattern=r"^t_", description="Tenant ID")
    scope: Dict[str, Any] = Field(..., description="Scope definition")
    type: MemoryType
    truth_mode: TruthMode
    state: Optional[MemoryState] = MemoryState.ACTIVE
    sensitivity: Optional[Dict[str, Any]] = None
    ownership: Dict[str, Any] = Field(..., description="Ownership information")
    temporal: Dict[str, Any] = Field(..., description="Temporal information")
    content: Dict[str, Any] = Field(..., description="Content")
    affect: Optional[Dict[str, Any]] = None
    impact_payload: Optional[Dict[str, Any]] = None
    seed_payload: Optional[Dict[str, Any]] = None
    procedural_payload: Optional[Dict[str, Any]] = None
    somatic_payload: Optional[Dict[str, Any]] = None
    strength: Optional[Dict[str, Any]] = None
    provenance: Dict[str, Any] = Field(..., description="Provenance information")
    reconsolidation_policy: Optional[str] = None


class MemoryCreateResponseV2(BaseModel):
    """Response from memory creation (v2)."""
    id: str
    tenant_id: str
    state: MemoryState
    created_at: datetime
    policy_trace: Dict[str, Any] = Field(default_factory=dict)


# ============================================================================
# Memory Query (POST /v2/memories/query)
# ============================================================================

class MemoryQueryRequestV2(BaseModel):
    """Request to query memories (v2)."""
    tenant_id: str = Field(..., pattern=r"^t_")
    scope: Dict[str, Any]
    purpose: PurposeType
    query_text: Optional[str] = None
    filters: Optional[Dict[str, Any]] = Field(default_factory=dict)
    limit: int = Field(default=50, ge=1, le=1000)


class MemoryQueryResponseV2(BaseModel):
    """Response from memory query (v2)."""
    memory_ids: List[str] = Field(default_factory=list)
    impacts: List[Dict[str, Any]] = Field(default_factory=list)  # Constraint objects
    seeds: List[Dict[str, Any]] = Field(default_factory=list)
    events: List[str] = Field(default_factory=list)  # Only non-sealed events
    denied_ids: List[str] = Field(default_factory=list)
    policy_trace: Dict[str, Any] = Field(default_factory=dict)
    access_log_id: str


# ============================================================================
# Reconstruction (POST /v2/reconstruct)
# ============================================================================

class ReconstructRequestV2(BaseModel):
    """Request to reconstruct context (v2)."""
    tenant_id: str = Field(..., pattern=r"^t_")
    scope: Dict[str, Any]
    purpose: PurposeType
    query_text: Optional[str] = None
    include_events: bool = Field(default=False, description="Include events (requires explicit consent)")


class ReconstructResponseV2(BaseModel):
    """Response from reconstruction (v2)."""
    reconstructed_context: str
    confidence: float = Field(ge=0.0, le=1.0)
    sources: Dict[str, List[str]] = Field(default_factory=dict)  # {impacts: [], seeds: [], events: []}
    policy_trace: Dict[str, Any] = Field(default_factory=dict)
    access_log_id: str


# ============================================================================
# Memory Operations
# ============================================================================

class SealMemoryRequestV2(BaseModel):
    """Request to seal a memory."""
    tenant_id: str = Field(..., pattern=r"^t_")
    reason: Optional[str] = None


class SealMemoryResponseV2(BaseModel):
    """Response from sealing a memory."""
    id: str
    state: MemoryState
    sealed_at: datetime


class RevokeMemoryRequestV2(BaseModel):
    """Request to revoke a memory."""
    tenant_id: str = Field(..., pattern=r"^t_")
    reason: Optional[str] = None


class RevokeMemoryResponseV2(BaseModel):
    """Response from revoking a memory."""
    id: str
    state: MemoryState
    revoked_at: datetime
    propagated_to: List[str] = Field(default_factory=list)  # Derived memory IDs


class ReinforceMemoryRequestV2(BaseModel):
    """Request to reinforce a memory."""
    tenant_id: str = Field(..., pattern=r"^t_")
    strength_delta: Optional[float] = Field(default=0.1, ge=0.0, le=1.0)


class ReinforceMemoryResponseV2(BaseModel):
    """Response from reinforcing a memory."""
    id: str
    strength: Dict[str, Any]
    reinforced_at: datetime


class RecallMemoryRequestV2(BaseModel):
    """Request to recall (reconsolidate) a memory."""
    tenant_id: str = Field(..., pattern=r"^t_")
    updates: Dict[str, Any] = Field(default_factory=dict)


class RecallMemoryResponseV2(BaseModel):
    """Response from recalling a memory."""
    id: str
    updated_at: datetime
    reconsolidation_trace: List[Dict[str, Any]] = Field(default_factory=list)


# ============================================================================
# Governance
# ============================================================================

class DisputeMemoryRequestV2(BaseModel):
    """Request to dispute a memory."""
    tenant_id: str = Field(..., pattern=r"^t_")
    reason: str
    new_dispute_state: DisputeState


class DisputeMemoryResponseV2(BaseModel):
    """Response from disputing a memory."""
    id: str
    dispute_state: DisputeState
    disputed_at: datetime


class AttestMemoryRequestV2(BaseModel):
    """Request to attest to a memory."""
    tenant_id: str = Field(..., pattern=r"^t_")
    attestation: str


class AttestMemoryResponseV2(BaseModel):
    """Response from attesting to a memory."""
    id: str
    dispute_state: DisputeState
    attested_at: datetime


class BridgeScopeRequestV2(BaseModel):
    """Request to bridge scopes."""
    tenant_id: str = Field(..., pattern=r"^t_")
    from_scope: Dict[str, Any]
    to_scope: Dict[str, Any]
    allow_events: bool = Field(default=False)
    allow_impacts: bool = Field(default=True)


class BridgeScopeResponseV2(BaseModel):
    """Response from bridging scopes."""
    bridged_memory_ids: List[str] = Field(default_factory=list)
    bridged_at: datetime


# ============================================================================
# Observability
# ============================================================================

class ExplainRequestV2(BaseModel):
    """Request to explain a decision."""
    tenant_id: str = Field(..., pattern=r"^t_")
    access_log_id: Optional[str] = None
    memory_ids: Optional[List[str]] = None
    request_context: Optional[Dict[str, Any]] = None


class ExplainResponseV2(BaseModel):
    """Response from explain request."""
    explanation: Dict[str, Any]
    memory_ids_used: List[str] = Field(default_factory=list)
    constraints_applied: List[Dict[str, Any]] = Field(default_factory=list)
    denials: List[Dict[str, Any]] = Field(default_factory=list)
    spiral_state: Optional[Dict[str, Any]] = None
    tool_gate_decision: Optional[Dict[str, Any]] = None
    reinforcement_blocked: Optional[str] = None


class ReplayRequestV2(BaseModel):
    """Request to replay a request."""
    tenant_id: str = Field(..., pattern=r"^t_")
    access_log_id: str
    override_context: Optional[Dict[str, Any]] = None


class ReplayResponseV2(BaseModel):
    """Response from replay request."""
    result: Dict[str, Any]
    policy_trace: Dict[str, Any] = Field(default_factory=dict)
    access_log_id: str

