import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.database import get_db, get_default_app, check_database_health
from app.models import App, Memory, ReadGrant, AuditEvent
from app.schemas import (
    MemoryCreateRequest,
    MemoryCreateResponse,
    MemoryReadRequest,
    MemoryReadResponse,
    MemoryReadContinueRequest,
    MemoryRevokeRequest,
    MemoryRevokeResponse,
)
from app.utils import (
    hash_revocation_token,
    normalize_purpose,
    check_policy,
    normalize_value_json,
    merge_memories_deterministic,
)
from app.sanitization import (
    sanitize_user_id,
    sanitize_scope,
    sanitize_domain,
    sanitize_purpose,
    sanitize_source,
    sanitize_json_value,
)
from app.memoryscope.v2_api import router as v2_router
from app.config import settings
from app.logging_config import setup_logging, get_logger
from app.middleware import RequestIDMiddleware, PerformanceMiddleware
from app.monitoring import setup_sentry
from app.errors import (
    APIError,
    format_error_response,
    api_error_handler,
    http_exception_handler,
    validation_exception_handler,
    generic_exception_handler,
)

# Setup logging first
setup_logging(use_json=(settings.log_format.lower() == "json"))
logger = get_logger(__name__)

# Setup Sentry if configured
sentry = setup_sentry()

app = FastAPI(
    title="MemoryScope API",
    version="0.1.0",
    description="""
    MemoryScope API - Store and retrieve user memories with policy enforcement.
    
    ## Features
    
    * **Memory Management**: Create, read, continue, and revoke user memories
    * **Policy Enforcement**: Purpose-based access; read denied if purpose not allowed for scope
    * **Deterministic Merging**: Same inputs produce the same merged summary
    * **Revocation Tokens**: Read returns a token for continue or revoke
    * **Audit Logging**: All operations written to audit_events
    
    ## Error Responses
    
    Errors follow a standard format:
    ```json
    {
      "error": {
        "code": "ERROR_CODE",
        "message": "Human-readable message",
        "request_id": "uuid",
        "timestamp": "ISO8601",
        "details": {},
        "hint": "Recovery suggestion"
      }
    }
    ```
    """,
    contact={
        "name": "API Support",
        "url": "https://yourdomain.com/contact",
    },
    license_info={
        "name": "Proprietary",
    },
)

# Add middleware (order matters - RequestID first)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(PerformanceMiddleware)

# Add error handlers
app.add_exception_handler(APIError, api_error_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

@app.on_event("startup")
async def startup_event():
    """Initialize services on application startup."""
    logger.info("Starting application...")
    errors = settings.validate_required()
    if errors:
        critical = [e for e in errors if "DATABASE_URL" in e]
        if critical:
            raise ValueError(f"Configuration errors: {', '.join(critical)}")
        for e in errors:
            logger.warning(f"Config: {e}")
    db_health = check_database_health()
    if db_health["status"] == "healthy":
        logger.info(f"Database healthy (response_time_ms: {db_health.get('response_time_ms', 0)})")
    else:
        logger.error(f"Database health check failed: {db_health.get('error')}")
    logger.info("Application startup complete")

# Include v2 API router
app.include_router(v2_router)

# Add CORS middleware with configuration from settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=settings.get_cors_headers(),
)


@app.get("/healthz")
def healthcheck():
    """
    Enhanced health check endpoint.
    Returns application health status including database connectivity.
    """
    import platform
    import sys
    
    health = {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "version": app.version,
    }
    
    # Database health
    db_health = check_database_health()
    health["database"] = db_health
    
    # Overall status
    if db_health["status"] != "healthy":
        health["status"] = "degraded"
    
    return health


@app.get("/healthz/ready")
def readiness_check():
    """
    Readiness probe endpoint.
    Returns 200 only if the application is ready to serve traffic.
    """
    db_health = check_database_health()
    
    if db_health["status"] != "healthy":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database not available"
        )
    
    return {"status": "ready"}


@app.get("/healthz/live")
def liveness_check():
    """
    Liveness probe endpoint.
    Returns 200 if the application is running.
    """
    return {"status": "alive"}


def _get_app(db: Session = Depends(get_db)) -> App:
    """Dependency: return the default app (core API, no API keys)."""
    return get_default_app(db)


def create_audit_event(
    db: Session,
    event_type: str,
    app_id: uuid.UUID,
    user_id: str = None,
    scope: str = None,
    domain: str = None,
    purpose: str = None,
    purpose_class: str = None,
    memory_ids: list[uuid.UUID] = None,
    revocation_grant_id: uuid.UUID = None,
    reason_code: str = None,
    meta: dict = None,
):
    """Create an audit event."""
    event = AuditEvent(
        event_type=event_type,
        app_id=app_id,
        user_id=user_id,
        scope=scope,
        domain=domain,
        purpose=purpose,
        purpose_class=purpose_class,
        memory_ids=memory_ids,
        revocation_grant_id=revocation_grant_id,
        reason_code=reason_code,
        meta=meta,
    )
    db.add(event)
    db.commit()


@app.post(
    "/memory",
    response_model=MemoryCreateResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "Memory created successfully"},
        400: {"description": "Validation error"},
    400: {"description": "Validation error"},
    },
    summary="Create a new memory",
    description="Create a new memory. value_json must match an allowed shape for the scope.",
    tags=["memories"],
)
def create_memory(
    memory_request: MemoryCreateRequest,
    app: App = Depends(_get_app),
    db: Session = Depends(get_db),
):
    """
    Create a new memory.
    
    Stores user memory data with automatic expiration based on TTL.
    The value_json is validated against allowed shapes for the given scope.
    """
    # Sanitize input
    try:
        user_id = sanitize_user_id(memory_request.user_id)
        scope = sanitize_scope(memory_request.scope)
        domain = sanitize_domain(memory_request.domain) if memory_request.domain else None
        source = sanitize_source(memory_request.source)
        # Sanitize JSON value (recursively escape HTML in strings)
        value_json = sanitize_json_value(memory_request.value_json)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    
    # Detect value shape
    shape = MemoryCreateRequest._detect_shape(value_json)
    if shape is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="value_json does not match any allowed shape",
        )

    # Normalize value_json
    normalized_value = normalize_value_json(value_json, shape)

    # Calculate expires_at
    created_at = datetime.utcnow()
    expires_at = created_at + timedelta(days=memory_request.ttl_days)

    # Create memory
    memory = Memory(
        user_id=user_id,
        scope=scope,
        domain=domain,
        value_json=normalized_value,
        value_shape=shape,
        source=memory_request.source,
        ttl_days=memory_request.ttl_days,
        created_at=created_at,
        expires_at=expires_at,
        app_id=app.id,
    )
    db.add(memory)
    db.commit()
    db.refresh(memory)

    # Audit
    create_audit_event(
        db=db,
        event_type="MEMORY_WRITE",
        app_id=app.id,
        user_id=user_id,
        scope=scope,
        domain=domain,
        memory_ids=[memory.id],
    )

    return MemoryCreateResponse(
        id=memory.id,
        user_id=memory.user_id,
        scope=memory.scope,
        domain=memory.domain,
        created_at=memory.created_at,
        expires_at=memory.expires_at,
    )


def _query_and_merge_memories(
    db: Session,
    app: App,
    user_id: str,
    scope: str,
    domain: Optional[str],
    max_age_days: Optional[int],
) -> tuple[Dict[str, Any], list[uuid.UUID]]:
    """Helper function to query and merge memories. Returns (merged_result, memory_ids)."""
    # Query memories
    query = db.query(Memory).filter(
        and_(
            Memory.user_id == user_id,
            Memory.scope == scope,
            Memory.expires_at > datetime.utcnow(),
            Memory.app_id == app.id,
        )
    )

    if domain:
        query = query.filter(Memory.domain == domain)
    else:
        query = query.filter(Memory.domain.is_(None))

    if max_age_days:
        cutoff = datetime.utcnow() - timedelta(days=max_age_days)
        query = query.filter(Memory.created_at >= cutoff)

    memories = query.order_by(Memory.created_at.desc()).limit(50).all()

    # Get memory IDs for audit
    memory_ids = [m.id for m in memories]

    # Convert to dicts for merging
    memory_dicts = [
        {
            "id": m.id,
            "value_json": m.value_json,
            "value_shape": m.value_shape,
            "created_at": m.created_at,
        }
        for m in memories
    ]

    # Deterministic merge
    merged = merge_memories_deterministic(memory_dicts, scope)
    return merged, memory_ids


@app.post(
    "/memory/read",
    response_model=MemoryReadResponse,
    responses={
        200: {"description": "Memories retrieved successfully"},
        400: {"description": "Validation error"},
        403: {"description": "Policy denied - purpose not allowed for scope"},
    },
    summary="Read memories with policy enforcement",
    description="Read and merge memories. Purpose must be allowed for scope. Returns revocation_token for continue/revoke.",
    tags=["memories"],
)
def read_memory(
    read_request: MemoryReadRequest,
    app: App = Depends(_get_app),
    db: Session = Depends(get_db),
):
    """
    Read memories with policy enforcement.
    
    Merges all active memories for the user/scope/domain and returns a summary.
    The purpose is validated against the policy matrix.
    """
    # Sanitize input
    try:
        user_id = sanitize_user_id(read_request.user_id)
        scope = sanitize_scope(read_request.scope)
        domain = sanitize_domain(read_request.domain) if read_request.domain else None
        purpose = sanitize_purpose(read_request.purpose)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    
    # Normalize purpose to purpose_class
    purpose_class = normalize_purpose(purpose)

    # Check policy (fail closed)
    if not check_policy(scope, purpose_class):
        create_audit_event(
            db=db,
            event_type="MEMORY_READ",
            app_id=app.id,
            user_id=user_id,
            scope=scope,
            domain=domain,
            purpose=purpose,
            purpose_class=purpose_class,
            reason_code="POLICY_DENIED",
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Purpose class '{purpose_class}' not allowed for scope '{scope}'",
        )

    # Query and merge memories
    merged, memory_ids = _query_and_merge_memories(
        db=db,
        app=app,
        user_id=user_id,
        scope=scope,
        domain=domain,
        max_age_days=read_request.max_age_days,
    )

    # Create read_grant
    revocation_token = str(uuid.uuid4())
    token_hash = hash_revocation_token(revocation_token)
    created_at = datetime.utcnow()
    expires_at = created_at + timedelta(hours=24)

    read_grant = ReadGrant(
        revocation_token_hash=token_hash,
        user_id=read_request.user_id,
        app_id=app.id,
        scope=read_request.scope,
        domain=read_request.domain,
        purpose=read_request.purpose,
        purpose_class=purpose_class,
        max_age_days=read_request.max_age_days,
        created_at=created_at,
        expires_at=expires_at,
    )
    db.add(read_grant)
    db.commit()
    db.refresh(read_grant)

    # Audit
    create_audit_event(
        db=db,
        event_type="MEMORY_READ",
        app_id=app.id,
        user_id=user_id,
        scope=scope,
        domain=domain,
        purpose=purpose,
        purpose_class=purpose_class,
        memory_ids=memory_ids if memory_ids else None,
        revocation_grant_id=read_grant.id,
    )

    return MemoryReadResponse(
        summary_text=merged["summary_text"],
        summary_struct=merged["summary_struct"],
        confidence=merged["confidence"],
        revocation_token=revocation_token,
        expires_at=expires_at,
    )


@app.post(
    "/memory/read/continue",
    response_model=MemoryReadResponse,
    responses={
        200: {"description": "Memories retrieved successfully"},
        400: {"description": "Validation error"},
        403: {"description": "Token revoked or expired"},
        404: {"description": "Token not found"},
    },
    summary="Continue reading with revocation token",
    description="Continue reading using a revocation token from a previous read.",
    tags=["memories"],
)
def continue_read_memory(
    continue_request: MemoryReadContinueRequest,
    app: App = Depends(_get_app),
    db: Session = Depends(get_db),
):
    """Continue reading memories using an existing revocation token."""
    token_hash = hash_revocation_token(continue_request.revocation_token)

    # Find the read grant
    read_grant = db.query(ReadGrant).filter(
        and_(
            ReadGrant.revocation_token_hash == token_hash,
            ReadGrant.app_id == app.id,
        )
    ).first()

    if read_grant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Revocation token not found",
        )

    # Check if revoked
    if read_grant.revoked_at is not None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="REVOKED",
        )

    # Check if expired
    if read_grant.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="REVOKED",
        )

    # Use max_age_days from request if provided, otherwise from grant
    max_age_days = continue_request.max_age_days if continue_request.max_age_days is not None else read_grant.max_age_days

    # Query and merge memories using grant's parameters
    merged, memory_ids = _query_and_merge_memories(
        db=db,
        app=app,
        user_id=read_grant.user_id,
        scope=read_grant.scope,
        domain=read_grant.domain,
        max_age_days=max_age_days,
    )

    # Audit
    create_audit_event(
        db=db,
        event_type="MEMORY_READ",
        app_id=app.id,
        user_id=read_grant.user_id,
        scope=read_grant.scope,
        domain=read_grant.domain,
        purpose=read_grant.purpose,
        purpose_class=read_grant.purpose_class,
        revocation_grant_id=read_grant.id,
        reason_code="CONTINUE",
    )

    return MemoryReadResponse(
        summary_text=merged["summary_text"],
        summary_struct=merged["summary_struct"],
        confidence=merged["confidence"],
        revocation_token=continue_request.revocation_token,  # Return same token
        expires_at=read_grant.expires_at,
    )


@app.post(
    "/memory/revoke",
    response_model=MemoryRevokeResponse,
    responses={
        200: {"description": "Memory access revoked successfully"},
        400: {"description": "Validation error"},
        404: {"description": "Token not found or already revoked"},
    },
    summary="Revoke memory access",
    description="Revoke a read grant. The token cannot be used to continue reading after revocation.",
    tags=["memories"],
)
def revoke_memory(
    revoke_request: MemoryRevokeRequest,
    app: App = Depends(_get_app),
    db: Session = Depends(get_db),
):
    """Revoke a read grant."""
    token_hash = hash_revocation_token(revoke_request.revocation_token)

    read_grant = db.query(ReadGrant).filter(
        and_(
            ReadGrant.revocation_token_hash == token_hash,
            ReadGrant.app_id == app.id,
        )
    ).first()

    if read_grant is None or read_grant.revoked_at is not None:
        # Don't leak information - return 404
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Revocation token not found",
        )

    # Revoke
    revoked_at = datetime.utcnow()
    read_grant.revoked_at = revoked_at
    read_grant.revoke_reason = "user_requested"
    db.commit()

    # Audit
    create_audit_event(
        db=db,
        event_type="MEMORY_REVOKE",
        app_id=app.id,
        user_id=read_grant.user_id,
        scope=read_grant.scope,
        domain=read_grant.domain,
        revocation_grant_id=read_grant.id,
    )

    return MemoryRevokeResponse(
        revoked=True,
        revoked_at=revoked_at,
    )

