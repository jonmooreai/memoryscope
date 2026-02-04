import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Column,
    ForeignKey,
    Integer,
    String,
    Text,
    DateTime,
    JSON,
    ARRAY,
    Index,
    Boolean,
    Numeric,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.database import Base


class App(Base):
    __tablename__ = "apps"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    api_key_hash = Column(String(255), unique=True, nullable=False)
    user_id = Column(Text, nullable=False)  # Link to user (Firebase UID)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    __table_args__ = (
        Index("idx_apps_user_id", "user_id"),
    )


class Memory(Base):
    __tablename__ = "memories"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(Text, nullable=False)
    scope = Column(String(50), nullable=False)
    domain = Column(Text, nullable=True)
    value_json = Column(JSONB, nullable=False)
    value_shape = Column(String(50), nullable=False)
    source = Column(String(50), nullable=False)
    ttl_days = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    app_id = Column(UUID(as_uuid=True), ForeignKey("apps.id"), nullable=False)

    app = relationship("App")

    __table_args__ = (
        Index("idx_memories_user_scope_domain_created", "user_id", "scope", "domain", "created_at"),
        Index("idx_memories_expires_at", "expires_at"),
    )


class ReadGrant(Base):
    __tablename__ = "read_grants"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    revocation_token_hash = Column(String(255), unique=True, nullable=False)
    user_id = Column(Text, nullable=False)
    app_id = Column(UUID(as_uuid=True), ForeignKey("apps.id"), nullable=False)
    scope = Column(String(50), nullable=False)
    domain = Column(Text, nullable=True)
    purpose = Column(Text, nullable=False)
    purpose_class = Column(String(50), nullable=False)
    max_age_days = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    revoked_at = Column(DateTime, nullable=True)
    revoke_reason = Column(Text, nullable=True)

    app = relationship("App")


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    event_type = Column(String(50), nullable=False)
    user_id = Column(Text, nullable=True)
    app_id = Column(UUID(as_uuid=True), ForeignKey("apps.id"), nullable=True)
    scope = Column(String(50), nullable=True)
    domain = Column(Text, nullable=True)
    purpose = Column(Text, nullable=True)
    purpose_class = Column(String(50), nullable=True)
    memory_ids = Column(ARRAY(UUID(as_uuid=True)), nullable=True)
    revocation_grant_id = Column(UUID(as_uuid=True), nullable=True)
    reason_code = Column(String(50), nullable=True)
    meta = Column(JSONB, nullable=True)

    app = relationship("App")

    __table_args__ = (
        Index("idx_audit_user_timestamp", "user_id", "timestamp"),
        Index("idx_audit_app_timestamp", "app_id", "timestamp"),
        Index("idx_audit_event_type_timestamp", "event_type", "timestamp"),
    )


class SubscriptionPlan(Base):
    """Predefined subscription plans (Free, Pro, Enterprise)"""
    __tablename__ = "subscription_plans"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(50), unique=True, nullable=False)  # free, pro, enterprise
    display_name = Column(String(100), nullable=False)
    price_monthly = Column(Numeric(10, 2), nullable=False, default=0)
    price_yearly = Column(Numeric(10, 2), nullable=True)
    stripe_price_id_monthly = Column(String(255), nullable=True)
    stripe_price_id_yearly = Column(String(255), nullable=True)
    stripe_product_id = Column(String(255), nullable=True)
    requests_per_month = Column(Integer, nullable=False)
    memories_limit = Column(Integer, nullable=False)
    rate_limit_per_hour = Column(Integer, nullable=False)
    features = Column(JSONB, nullable=True)  # Array of feature strings
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class Subscription(Base):
    """User subscriptions linked to Stripe"""
    __tablename__ = "subscriptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(Text, nullable=False)  # Firebase UID
    plan_id = Column(UUID(as_uuid=True), ForeignKey("subscription_plans.id"), nullable=False)
    stripe_subscription_id = Column(String(255), unique=True, nullable=True)
    stripe_customer_id = Column(String(255), nullable=True)
    status = Column(String(50), nullable=False)  # active, canceled, past_due, trialing, etc.
    current_period_start = Column(DateTime, nullable=False)
    current_period_end = Column(DateTime, nullable=False)
    cancel_at_period_end = Column(Boolean, default=False, nullable=False)
    canceled_at = Column(DateTime, nullable=True)
    trial_end = Column(DateTime, nullable=True)
    overage_enabled = Column(Boolean, default=False, nullable=True)
    overage_limit = Column(Integer, nullable=True)  # Maximum overage API calls per month
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    plan = relationship("SubscriptionPlan")

    __table_args__ = (
        Index("idx_subscriptions_user_id", "user_id"),
        Index("idx_subscriptions_stripe_subscription_id", "stripe_subscription_id"),
        Index("idx_subscriptions_stripe_customer_id", "stripe_customer_id"),
    )


class MemoryV2(Base):
    """
    MemoryScope Core API v2 Memory Storage
    
    Stores complete MemoryObject as JSONB for flexibility while maintaining
    indexed fields for efficient querying.
    """
    __tablename__ = "memories_v2"

    id = Column(String(255), primary_key=True)  # mem_...
    tenant_id = Column(String(255), nullable=False, index=True)  # t_...
    
    # Scope (indexed for queries)
    scope_type = Column(String(50), nullable=False, index=True)
    scope_id = Column(String(255), nullable=False, index=True)
    
    # Core classification (indexed)
    type = Column(String(50), nullable=False, index=True)  # event, impact, seed
    truth_mode = Column(String(50), nullable=False, index=True)
    state = Column(String(50), nullable=False, index=True)  # active, sealed, etc.
    
    # Sensitivity (for policy filtering)
    sensitivity_level = Column(String(50), nullable=False, index=True)
    sensitivity_categories = Column(ARRAY(String), nullable=True)
    
    # Ownership (for dispute filtering)
    dispute_state = Column(String(50), nullable=False, index=True)
    
    # Temporal (for decay and filtering)
    occurred_at_observed = Column(DateTime, nullable=False, index=True)
    occurred_at_claimed = Column(DateTime, nullable=True)
    
    # Strength (for decay)
    strength_current = Column(Numeric(3, 2), nullable=False, default=0.75)
    last_reinforced_at = Column(DateTime, nullable=True)
    
    # Complete memory object as JSONB
    memory_object_json = Column(JSONB, nullable=False)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Links to app (for multi-tenancy)
    app_id = Column(UUID(as_uuid=True), ForeignKey("apps.id"), nullable=False, index=True)
    
    app = relationship("App")

    __table_args__ = (
        Index("idx_memories_v2_tenant_scope", "tenant_id", "scope_type", "scope_id"),
        Index("idx_memories_v2_state_type", "state", "type"),
        Index("idx_memories_v2_truth_mode", "truth_mode"),
        Index("idx_memories_v2_occurred_at", "occurred_at_observed"),
        Index("idx_memories_v2_created_at", "created_at"),
    )


class MemoryLinkV2(Base):
    """Links between parent and child memories (derived relationships)."""
    __tablename__ = "memory_links_v2"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    parent_id = Column(String(255), nullable=False, index=True)  # mem_...
    child_id = Column(String(255), nullable=False, index=True)  # mem_...
    relationship = Column(String(50), nullable=False)  # derived_impact, derived_seed, etc.
    rule = Column(String(255), nullable=False)
    strength_transfer = Column(Numeric(3, 2), nullable=False, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    __table_args__ = (
        Index("idx_memory_links_v2_parent", "parent_id"),
        Index("idx_memory_links_v2_child", "child_id"),
        Index("idx_memory_links_v2_relationship", "relationship"),
    )


class AccessLogV2(Base):
    """Access log entries for v2 API (PRD v2.2 Section 2.3)."""
    __tablename__ = "access_logs_v2"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    log_id = Column(String(255), unique=True, nullable=False, index=True)  # log_...
    time = Column(DateTime, nullable=False, index=True)
    tenant_id = Column(String(255), nullable=False, index=True)
    
    # Caller info
    caller_client_id = Column(String(255), nullable=True)
    caller_user_id = Column(String(255), nullable=True, index=True)
    caller_ip = Column(String(45), nullable=True)
    
    # Scope
    scope_type = Column(String(50), nullable=False)
    scope_id = Column(String(255), nullable=False)
    
    # Purpose
    purpose = Column(String(50), nullable=False, index=True)
    
    # Query
    query_text = Column(Text, nullable=True)
    query_op = Column(String(50), nullable=True)
    
    # Decision
    decision_allowed = Column(Boolean, nullable=False)
    decision_returned_ids = Column(ARRAY(String), nullable=True)
    decision_denied_ids = Column(ARRAY(String), nullable=True)
    decision_matched_rules = Column(ARRAY(String), nullable=True)
    decision_explanation = Column(Text, nullable=True)
    
    # Complete log entry as JSONB
    access_log_json = Column(JSONB, nullable=False)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    __table_args__ = (
        Index("idx_access_logs_v2_tenant_time", "tenant_id", "time"),
        Index("idx_access_logs_v2_purpose", "purpose"),
        Index("idx_access_logs_v2_scope", "scope_type", "scope_id"),
    )


class SpiralArtifactV2(Base):
    """ThoughtPatternArtifact storage (ephemeral, TTL-based)."""
    __tablename__ = "spiral_artifacts_v2"

    id = Column(String(255), primary_key=True)  # tpa_...
    tenant_id = Column(String(255), nullable=False, index=True)
    scope_type = Column(String(50), nullable=False)
    scope_id = Column(String(255), nullable=False)
    pattern_type = Column(String(50), nullable=False, index=True)
    confidence = Column(Numeric(3, 2), nullable=False, default=0.0)
    signals = Column(ARRAY(String), nullable=True)
    window_start = Column(DateTime, nullable=False)
    window_end = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False, index=True)
    
    # Complete artifact as JSONB
    artifact_json = Column(JSONB, nullable=False)
    
    __table_args__ = (
        Index("idx_spiral_artifacts_v2_tenant_scope", "tenant_id", "scope_type", "scope_id"),
        Index("idx_spiral_artifacts_v2_expires_at", "expires_at"),
    )

