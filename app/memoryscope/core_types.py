"""
MemoryScope Core API - Canonical Type Definitions
PRD v2.2 Implementation

This module defines all canonical types for the MemoryScope Core API.
All types follow the PRD v2.2 specification exactly.
"""
from datetime import datetime
from typing import Optional, Dict, Any, List, Literal, Union
from uuid import UUID
from enum import Enum
from pydantic import BaseModel, Field, field_validator, model_validator


# ============================================================================
# Enums - Canonical Values
# ============================================================================

class MemoryType(str, Enum):
    """Memory object types (persistent)."""
    EVENT = "event"
    IMPACT = "impact"
    SEED = "seed"


class TruthMode(str, Enum):
    """Truth modes (mandatory, immutable)."""
    FACTUAL_CLAIM = "factual_claim"
    SUBJECTIVE_EXPERIENCE = "subjective_experience"
    COUNTERFACTUAL = "counterfactual"
    IMAGINED = "imagined"
    SOCIALLY_SOURCED = "socially_sourced"
    PROCEDURAL = "procedural"
    SOMATIC = "somatic"
    IDENTITY_ROLE_BOUND = "identity_role_bound"


class MemoryState(str, Enum):
    """Memory states (persistent)."""
    ACTIVE = "active"
    RESTRICTED = "restricted"
    SEALED = "sealed"
    DORMANT = "dormant"
    REVOKED = "revoked"
    TOMBSTONED = "tombstoned"


class OwnerType(str, Enum):
    """Ownership types."""
    USER = "user"
    GROUP = "group"
    ORG = "org"
    SYSTEM = "system"
    EXTERNAL_SOURCE = "external_source"


class DisputeState(str, Enum):
    """Dispute states."""
    UNDISPUTED = "undisputed"
    UNVERIFIED = "unverified"
    DISPUTED = "disputed"
    CONTESTED = "contested"


class Visibility(str, Enum):
    """Visibility levels."""
    PRIVATE = "private"
    SHARED_WITH_GROUP = "shared_with_group"
    SHARED_WITH_ORG = "shared_with_org"
    RESTRICTED_REVIEW = "restricted_review"


class SensitivityLevel(str, Enum):
    """Sensitivity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SensitivityHandling(str, Enum):
    """Sensitivity handling modes."""
    NORMAL = "normal"
    NO_PROMPT = "no_prompt"
    NO_SEARCH = "no_search"
    SEALED_DEFAULT = "sealed_default"


class TimePrecision(str, Enum):
    """Time precision levels."""
    EXACT = "exact"
    APPROXIMATE = "approximate"
    RANGE = "range"
    UNKNOWN = "unknown"


class DecayModel(str, Enum):
    """Decay models."""
    HALF_LIFE = "half_life"
    LINEAR = "linear"
    LOGARITHMIC = "logarithmic"
    STEP = "step"


class ReconsolidationPolicy(str, Enum):
    """Reconsolidation policies."""
    NEVER_EDIT_SOURCE = "never_edit_source"
    APPEND_ONLY = "append_only"
    ALLOW_RELABEL_AFFECT_ONLY = "allow_relabel_affect_only"
    ALLOW_UPDATE_CLAIM_CONFIDENCE = "allow_update_claim_confidence"


class SourceType(str, Enum):
    """Provenance source types."""
    USER = "user"
    SYSTEM = "system"
    IMPORT = "import"
    HUMAN_AGENT = "human_agent"


class SurfaceType(str, Enum):
    """Provenance surface types."""
    CHAT = "chat"
    EMAIL = "email"
    TICKET = "ticket"
    CALL_SUMMARY = "call_summary"
    FORM = "form"


class ScopeType(str, Enum):
    """Scope types."""
    USER = "user"
    ORG = "org"
    APP = "app"
    SESSION = "session"
    PROJECT = "project"
    CASE = "case"
    ROLE = "role"


class ConstraintKind(str, Enum):
    """Constraint kinds."""
    AVOID = "avoid"
    PREFER = "prefer"
    REQUIRE = "require"
    TONE = "tone"
    STYLE = "style"
    BOUNDARY = "boundary"
    SAFETY = "safety"
    CLARIFY_FIRST = "clarify_first"
    ASK_PERMISSION = "ask_permission"


class ConstraintTarget(str, Enum):
    """Constraint targets."""
    RESPONSE = "response"
    PROMPT_CONTEXT = "prompt_context"
    TOOL_EXECUTION = "tool_execution"
    MEMORY_OPS = "memory_ops"


class MergeStrategy(str, Enum):
    """Merge strategies for constraints."""
    LATEST_WINS = "latest_wins"
    MAX_WEIGHT = "max_weight"
    MIN_WEIGHT = "min_weight"
    UNION = "union"
    INTERSECTION = "intersection"
    APPEND_ONLY = "append_only"


class PurposeType(str, Enum):
    """Access purpose types."""
    CHAT_RESPONSE = "chat_response"
    TASK_EXECUTION = "task_execution"
    SAFETY_FILTERING = "safety_filtering"
    REFLECTION_REQUESTED_BY_USER = "reflection_requested_by_user"
    SUPPORT_AGENT_REVIEW = "support_agent_review"
    COMPLIANCE_AUDIT = "compliance_audit"
    DEBUGGING_REPLAY = "debugging_replay"


class PatternType(str, Enum):
    """Spiral pattern types."""
    CATASTROPHIC_PROJECTION = "catastrophic_projection"
    RUNAWAY_COUNTERFACTUAL = "runaway_counterfactual"
    CERTAINTY_INFLATION = "certainty_inflation"
    FUTURE_COLLAPSE = "future_collapse"
    NEGATIVE_FEEDBACK_LOOP = "negative_feedback_loop"


# ============================================================================
# Nested Models
# ============================================================================

class Scope(BaseModel):
    """Scope definition."""
    scope_type: ScopeType
    scope_id: str
    flags: Optional[Dict[str, Any]] = Field(default_factory=dict)


class Sensitivity(BaseModel):
    """Sensitivity classification."""
    level: SensitivityLevel
    categories: List[str] = Field(default_factory=list)  # trauma, shame, moral_injury, etc.
    handling: SensitivityHandling = SensitivityHandling.NORMAL


class Ownership(BaseModel):
    """Ownership and dispute model."""
    owner_type: OwnerType
    owners: List[str] = Field(default_factory=list)  # principal IDs
    claimant: str  # principal ID
    subjects: List[str] = Field(default_factory=list)  # principal IDs (who the memory is about)
    dispute_state: DisputeState = DisputeState.UNDISPUTED
    visibility: Visibility = Visibility.PRIVATE


class Temporal(BaseModel):
    """Temporal semantics."""
    occurred_at_observed: datetime  # ingest time, always available
    occurred_at_claimed: Optional[datetime] = None
    time_precision: TimePrecision = TimePrecision.UNKNOWN
    time_confidence: float = Field(ge=0.0, le=1.0, default=0.0)
    range: Optional[Dict[str, datetime]] = None  # {start, end}
    ordering_uncertainty: bool = False


class Content(BaseModel):
    """Content definition."""
    format: Literal["text", "json"] = "text"
    language: str = "en"
    text: Optional[str] = None
    json: Optional[Dict[str, Any]] = None


class AffectEntry(BaseModel):
    """Single affect entry in history."""
    at: datetime
    labels: List[str] = Field(default_factory=list)
    valence: float = Field(ge=-1.0, le=1.0)
    arousal: float = Field(ge=0.0, le=1.0)
    reason: str


class Affect(BaseModel):
    """Affect classification."""
    valence: float = Field(ge=-1.0, le=1.0, default=0.0)
    arousal: float = Field(ge=0.0, le=1.0, default=0.0)
    labels: List[str] = Field(default_factory=list)
    affect_confidence: float = Field(ge=0.0, le=1.0, default=0.0)
    affect_history: List[AffectEntry] = Field(default_factory=list)


class ImpactPayload(BaseModel):
    """Impact payload (constraints)."""
    constraints: List[Dict[str, Any]] = Field(default_factory=list)  # Will be Constraint objects


class SeedActivation(BaseModel):
    """Seed activation parameters."""
    min_confidence: float = Field(ge=0.0, le=1.0, default=0.55)
    cooldown_seconds: int = Field(ge=0, default=3600)


class SeedPayload(BaseModel):
    """Seed payload."""
    cues: List[str] = Field(default_factory=list)
    activation: SeedActivation = Field(default_factory=SeedActivation)


class ProceduralPayload(BaseModel):
    """Procedural memory payload."""
    pattern: Optional[str] = None
    trigger_conditions: List[str] = Field(default_factory=list)
    recommended_interaction_protocol: List[str] = Field(default_factory=list)
    evidence: Dict[str, int] = Field(default_factory=dict)  # {observations: 0, window_days: 0}
    privacy_guard: str = "requires_explicit_opt_in"


class SomaticPayload(BaseModel):
    """Somatic memory payload."""
    triggers: List[str] = Field(default_factory=list)
    responses: List[str] = Field(default_factory=list)
    do_not_prompt_with: List[str] = Field(default_factory=list)


class Strength(BaseModel):
    """Memory strength and decay."""
    initial: float = Field(ge=0.0, le=1.0, default=0.75)
    current: float = Field(ge=0.0, le=1.0, default=0.75)
    decay_model: DecayModel = DecayModel.HALF_LIFE
    half_life_days: Optional[int] = None
    last_reinforced_at: Optional[datetime] = None


class TransformEntry(BaseModel):
    """Transform chain entry."""
    transform_id: str
    version: str
    run_id: str


class Provenance(BaseModel):
    """Provenance information."""
    source: SourceType
    surface: Optional[SurfaceType] = None
    conversation_id: Optional[str] = None
    derived_from: List[str] = Field(default_factory=list)  # memory IDs
    transform_chain: List[TransformEntry] = Field(default_factory=list)
    policy_version: Optional[str] = None
    confidence: float = Field(ge=0.0, le=1.0, default=0.0)


class HistoryEntry(BaseModel):
    """History entry."""
    at: datetime
    actor: str  # svc_x|user_y
    action: str  # created|sealed|revoked|reinforced|edited|decayed|recalled
    summary: str


class ReconsolidationTrace(BaseModel):
    """Reconsolidation trace entry."""
    at: datetime
    transform_id: str
    run_id: str


# ============================================================================
# Main MemoryObject Model
# ============================================================================

class MemoryObject(BaseModel):
    """
    Canonical MemoryObject schema (PRD v2.2 Section 2.1).
    
    All persistent memory objects MUST be exactly one of: event, impact, seed.
    Every memory object MUST have exactly one truth_mode, immutable after creation.
    """
    id: str = Field(..., pattern=r"^mem_")  # mem_...
    tenant_id: str = Field(..., pattern=r"^t_")  # t_...
    scope: Scope

    # Core classification
    type: MemoryType
    truth_mode: TruthMode
    state: MemoryState = MemoryState.ACTIVE

    # Sensitivity
    sensitivity: Sensitivity = Field(default_factory=lambda: Sensitivity(
        level=SensitivityLevel.LOW,
        categories=[],
        handling=SensitivityHandling.NORMAL
    ))

    # Ownership
    ownership: Ownership

    # Temporal
    temporal: Temporal

    # Content
    content: Content

    # Affect
    affect: Affect = Field(default_factory=Affect)

    # Type-specific payloads
    impact_payload: Optional[ImpactPayload] = None
    seed_payload: Optional[SeedPayload] = None
    procedural_payload: Optional[ProceduralPayload] = None
    somatic_payload: Optional[SomaticPayload] = None

    # Strength and decay
    strength: Strength = Field(default_factory=Strength)

    # Provenance
    provenance: Provenance

    # History
    history: List[HistoryEntry] = Field(default_factory=list)

    # Reconsolidation
    reconsolidation_policy: ReconsolidationPolicy = ReconsolidationPolicy.NEVER_EDIT_SOURCE
    reconsolidation_trace: List[ReconsolidationTrace] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_type_payloads(self):
        """Validate that type-specific payloads match the type."""
        if self.type == MemoryType.IMPACT and self.impact_payload is None:
            self.impact_payload = ImpactPayload()
        if self.type == MemoryType.SEED and self.seed_payload is None:
            self.seed_payload = SeedPayload()
        return self

    @model_validator(mode="after")
    def validate_truth_mode_rules(self):
        """Validate truth mode rules."""
        # Counterfactual and imagined MUST NEVER be treated as evidence for tool decisions
        # This is enforced at retrieval/tool gate level, not here
        return self

    @model_validator(mode="after")
    def validate_reconsolidation_defaults(self):
        """Set default reconsolidation policy based on type."""
        if self.reconsolidation_policy == ReconsolidationPolicy.NEVER_EDIT_SOURCE:
            if self.type == MemoryType.EVENT:
                self.reconsolidation_policy = ReconsolidationPolicy.NEVER_EDIT_SOURCE
            elif self.type == MemoryType.IMPACT:
                self.reconsolidation_policy = ReconsolidationPolicy.APPEND_ONLY
            elif self.type == MemoryType.SEED:
                self.reconsolidation_policy = ReconsolidationPolicy.APPEND_ONLY
        return self


# ============================================================================
# Constraint Models
# ============================================================================

class ConstraintMerge(BaseModel):
    """Constraint merge configuration."""
    slot: str
    strategy: MergeStrategy
    tie_breakers: List[str] = Field(default_factory=lambda: ["priority", "last_reinforced_at", "created_at", "constraint_id"])


class Constraint(BaseModel):
    """
    Impact Constraint Schema (PRD v2.2 Section 3.1).
    
    All constraints MUST be atomic, narrative-free.
    """
    constraint_id: str = Field(..., pattern=r"^con_")
    kind: ConstraintKind
    topic: str  # topic_id
    target: ConstraintTarget
    rule: str  # rule_id
    params: Dict[str, Any] = Field(default_factory=dict)
    weight: float = Field(default=0.0, ge=0.0)
    priority: int = Field(default=0)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    created_at: datetime
    expires_at: Optional[datetime] = None
    source_refs: List[str] = Field(default_factory=list)  # memory IDs
    provenance: Dict[str, Any] = Field(default_factory=dict)
    merge: ConstraintMerge


# ============================================================================
# Derived Object Link
# ============================================================================

class DerivedObjectLink(BaseModel):
    """Derived object link (PRD v2.2 Section 2.2)."""
    parent_id: str
    child_id: str
    relationship: Literal["derived_impact", "derived_seed", "summary_of", "supersedes"]
    rule: str
    strength_transfer: float = Field(ge=0.0, le=1.0, default=0.0)
    created_at: datetime


# ============================================================================
# Access Log Entry
# ============================================================================

class Caller(BaseModel):
    """Caller information."""
    client_id: Optional[str] = None
    user_id: Optional[str] = None
    ip: Optional[str] = None


class Query(BaseModel):
    """Query information."""
    text: Optional[str] = None
    op: Literal["ingest", "query", "reconstruct", "tool_gate", "reinforce", "recall", "revoke"]


class Decision(BaseModel):
    """Access decision."""
    allowed: bool
    returned_ids: List[str] = Field(default_factory=list)
    denied_ids: List[str] = Field(default_factory=list)
    matched_rules: List[str] = Field(default_factory=list)
    explanation: str = ""


class AccessLogEntry(BaseModel):
    """Access log entry (PRD v2.2 Section 2.3)."""
    log_id: str = Field(..., pattern=r"^log_")
    time: datetime
    tenant_id: str
    caller: Caller
    scope: Scope
    purpose: PurposeType
    query: Optional[Query] = None
    decision: Decision
    revocation_token: Optional[str] = None


# ============================================================================
# Spiral Detection Models
# ============================================================================

class ThoughtPatternArtifact(BaseModel):
    """
    ThoughtPatternArtifact (TPA) - Ephemeral, internal only (PRD v2.2 Section 8.2).
    
    TPA is ephemeral, internal-only artifact. Never exported.
    """
    id: str = Field(..., pattern=r"^tpa_")
    tenant_id: str
    scope: Scope
    pattern_type: PatternType
    confidence: float = Field(ge=0.0, le=1.0, default=0.0)
    signals: List[str] = Field(default_factory=list)
    window: Dict[str, datetime]  # {start, end}
    created_at: datetime
    expires_at: datetime
    associated_memory_refs: Dict[str, List[str]] = Field(default_factory=dict)  # {imagined: [], counterfactual: [], impacts: []}


# ============================================================================
# Utility Functions
# ============================================================================

def generate_memory_id() -> str:
    """Generate a memory ID in the format mem_..."""
    import uuid
    return f"mem_{uuid.uuid4().hex[:16]}"


def generate_constraint_id() -> str:
    """Generate a constraint ID in the format con_..."""
    import uuid
    return f"con_{uuid.uuid4().hex[:16]}"


def generate_tpa_id() -> str:
    """Generate a TPA ID in the format tpa_..."""
    import uuid
    return f"tpa_{uuid.uuid4().hex[:16]}"


def generate_log_id() -> str:
    """Generate a log ID in the format log_..."""
    import uuid
    return f"log_{uuid.uuid4().hex[:16]}"

