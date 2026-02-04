# MemoryScope API

Backend API for managing scoped user memories with policy enforcement and deterministic merging. Supports **v1** (scope-based preferences, constraints, etc.) and **v2** (MemoryScope Core types, policy DSL, sealed memories). No API keys or billing—core only.

## Features

- **Memory management**: Create, read, continue, and revoke user memories with TTL and scope/domain filtering
- **Policy enforcement**: Purpose-based access; read denied unless the purpose is allowed for the scope
- **Deterministic merging**: Same inputs produce the same merged summary for a scope
- **Revocation tokens**: Read returns a token for continue or revoke
- **Audit logging**: All operations write to `audit_events`

## Tech stack

- **Python 3.12**, **FastAPI**, **Pydantic v2**
- **PostgreSQL** (via SQLAlchemy + Alembic)
- **Docker Compose** for local API + DB
- **pytest** for tests

### High-level architecture

```mermaid
flowchart LR
    subgraph Client["Client / Your app"]
        C[Client]
    end

    subgraph API["MemoryScope API"]
        GW[Request ID + CORS]
        V1["v1 routes\n/memory, /memory/read\n/memory/revoke, ..."]
        V2["v2 routes\n/v2/..."]
    end

    subgraph Data["Data layer"]
        PG[(PostgreSQL\nmemories\nread_grants\naudit_events)]
    end

    C --> GW --> V1
    GW --> V2
    V1 --> PG
    V2 --> PG
```

- Requests are tagged with a request ID. **v1** and **v2** use the same DB; v1 is scope-based, v2 is MemoryScope Core (policy DSL, sealed memories). No API keys—single default app.

### v1 read flow (policy + revocation)

Reads are purpose-gated: the requested **purpose** must be allowed for the **scope**, or the API returns 403.

```mermaid
sequenceDiagram
    participant Client
    participant Server as MemoryScope API
    participant Policy as Policy matrix
    participant DB as PostgreSQL

    Client->>Server: POST /memory/read (user_id, scope, purpose, ...)
    Server->>Policy: purpose allowed for scope?
    alt purpose not allowed for scope
        Policy-->>Server: deny
        Server-->>Client: 403 Forbidden
    else purpose allowed
        Policy-->>Server: allow
        Server->>DB: Query memories (user_id, scope, domain, not expired)
        DB-->>Server: rows
        Server->>Server: Merge deterministically (same input → same summary)
        Server->>DB: Insert read_grant (revocation_token hashed)
        Server->>DB: Insert audit_events MEMORY_READ
        Server-->>Client: 200 { summary_text, summary_struct, revocation_token, ... }
    end
```

- **Continue read**: Client sends the same `revocation_token` to **POST /memory/read/continue**; API looks up the grant and re-runs the same merge (optional `max_age_days`). If the grant was revoked or expired → 403.
- **Revoke**: Client sends **POST /memory/revoke** with `revocation_token`; API sets `revoked_at` on the grant. Later continue with that token returns 403.

## Prerequisites

- **Docker** and **Docker Compose** (recommended), or
- **Python 3.12+** and a **PostgreSQL** instance for manual setup

## Quick start (Docker)

```bash
# 1. Clone and enter project
cd memoryscope-api

# 2. Environment
cp env.example .env
# Edit .env if needed (e.g. DATABASE_URL for custom Postgres)

# 3. Start services
docker compose up -d --build

# 4. Health check
curl http://localhost:8000/healthz
# => {"status":"ok"}

# 5. Run migrations
docker compose exec api alembic upgrade head

# 6. Run tests
docker compose exec api pytest -q
```

- **API base**: http://localhost:8000  
- **Interactive docs**: http://localhost:8000/docs  

No API keys; the API uses a single default app.

## Quick start (without Docker)

1. **PostgreSQL**: Create databases (e.g. `scoped_memory`, `scoped_memory_test`).
2. **Environment**:
   ```bash
   cp env.example .env
   # Set DATABASE_URL (and DATABASE_URL_TEST if you run tests)
   # Example: postgresql+psycopg://user:pass@localhost:5432/scoped_memory
   ```
3. **Dependencies**: `pip install -r requirements.txt`
4. **Migrations**: `alembic upgrade head`
5. **Run API**: `uvicorn app.main:app --reload`

## Environment variables

Copy `env.example` to `.env` and set `DATABASE_URL`. **Do not commit `.env`.**

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | Yes | Postgres URL, e.g. `postgresql+psycopg://user:pass@host:5432/dbname` |
| `DATABASE_URL_TEST` | For tests | Test DB URL (defaults to main DB name + `_test` if unset) |
| `LOG_LEVEL` | No | `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` |
| `LOG_FORMAT` | No | `json` or `human` |
| `CORS_ORIGINS` | No | Allowed origins, comma-separated |
| `CORS_ALLOW_CREDENTIALS` | No | Default true |
| `SENTRY_DSN` | No | Sentry DSN for error tracking |
| `ENVIRONMENT` | No | `development`, `staging`, `production` |
| `VALIDATE_CONFIG` | No | Set true to validate config on startup |

## API overview

### v1 endpoints (scope-based memories)

- **POST /memory** – Create a memory (user_id, scope, domain, source, ttl_days, value_json).  
  Allowed scopes: `preferences`, `constraints`, `communication`, `accessibility`, `schedule`, `attention`.  
  Value must match a supported shape (e.g. `likes_dislikes`, `kv_map`, `rules_list`).

- **POST /memory/read** – Read memories for a user/scope/domain with a **purpose**.  
  Returns a merged summary, confidence, and a **revocation_token**.  
  Policy: the purpose must be allowed for the scope (see [Scopes and policy](#scopes-and-policy)).

- **POST /memory/read/continue** – Continue reading using a previous **revocation_token** (optional `max_age_days`).  
  Returns 403 if the token was revoked or expired.

- **POST /memory/revoke** – Revoke a read grant by **revocation_token**.  
  After revocation, that token cannot be used for continue.

See http://localhost:8000/docs for request/response schemas.

### v2 endpoints (MemoryScope Core)

The v2 API under `/v2/` provides MemoryScope Core–style objects, policy DSL, and sealed-memory semantics.  
See **[app/memoryscope/README.md](app/memoryscope/README.md)** and the OpenAPI docs at `/docs` for details.

## Scopes and policy (v1)

| Scope | Example allowed purpose classes |
|-------|---------------------------------|
| preferences | content_generation, recommendation |
| constraints | recommendation, scheduling, task_execution |
| communication | content_generation, notification_delivery, ui_rendering |
| accessibility | ui_rendering, content_generation, notification_delivery |
| schedule | scheduling, task_execution |
| attention | notification_delivery, ui_rendering |

If the request purpose is not allowed for the scope, the read is denied (403).

## Value shapes (v1)

Supported shapes for `value_json` include: `kv_map`, `likes_dislikes`, `rules_list`, `schedule_windows`, `boolean_flags`, `attention_settings`.  
The API normalizes (e.g. dedupe, sort, lowercase) where applicable.

## Database and migrations

- **Alembic** is used for migrations; definitions live in `alembic/versions/`.
- Apply migrations: `alembic upgrade head` (or `docker compose exec api alembic upgrade head`).
- Create a new revision: `alembic revision -m "description"`.

Main tables: `apps` (one default row), `memories`, `read_grants`, `audit_events`. Billing tables exist from migrations but are unused.

## Testing

- **Unit/integration tests**: `pytest` (or `docker compose exec api pytest`).  
  Uses `DATABASE_URL_TEST` or a `_test` database. See **[tests/README.md](tests/README.md)** for structure and how to run specific tests.

- **Test app (OpenAI-backed runner)**: See **[test_app/README.md](test_app/README.md)** for the test app that generates realistic data and exercises the API.

## Demo

A minimal in-browser demo shows policy enforcement, scoped access, revocation, and audit behavior:

1. Start the API (e.g. `docker compose up -d`).
2. Open **demo/index.html** in a browser and run the flows (no API key needed).

See **[demo/README.md](demo/README.md)** for flow descriptions.

## Future features (v2 / roadmap)

Planned or in-progress capabilities, especially for the MemoryScope Core (v2) API:

| Feature | Description |
|--------|--------------|
| **Reconstruction engine** | Rebuilds context for a given purpose from **impacts** (constraints) and **seeds**, not raw events. Used to supply tool/chat context without leaking sealed or sensitive events. Implemented in `app/memoryscope/reconstruction.py`; endpoint exists; full integration and persistence still evolving. |
| **Spiral detection** | Detects “spiral” thought patterns (e.g. rumination, future collapse). When spiral state is active, policy can block new impact derivation or gate tool use. Core types include `ThoughtPatternArtifact`; policy DSL has `spiral` config; full detection pipeline and storage (e.g. `SpiralArtifactV2`) are planned. |
| **Retrieval engine with sealed filtering** | Policy-aware retrieval that **never returns sealed memories**. Returns impacts and seeds for a purpose; used by reconstruction and query endpoints. Skeleton in `app/memoryscope/retrieval.py`; sealed filtering and full indexing are in progress. |
| **Impact extraction and constraint merging** | **Deterministic** extraction of impacts (constraints) from events; policy controls whether derivation is allowed. Constraint merging for consistency across impacts. Implemented in `app/memoryscope/impact_extraction.py`; linking and storage wired for ingest; merging and conflict rules are future work. |
| **Observability (explain, replay)** | **Explain**: why a decision was made (policy trace, spiral state, tool gate). **Replay**: re-run a request for debugging. Observability engine and explain/replay endpoints exist; spiral state and some tool-gate details are still stubbed. |
| **V2 persistence and schema** | Full DB persistence for v2 memories: `memories_v2`, links, access logs, spiral artifacts. Migrations and models exist in part; complete schema migration and storage path for all v2 operations are planned. |
| **Seed derivation** | Derive **seeds** from events (similar to impacts) when policy allows. Policy DSL supports it; derivation logic and storage are not yet implemented. |
| **Recall, dispute, attestation** | **Recall**: reconsolidate or update memories with policy-gated rules. **Dispute**: mark facts as disputed and suppress in chat. **Attestation**: record attestations to facts. Endpoints are stubbed; behavior and storage are future work. |
| **Scope bridging** | Use or combine memories across scopes (e.g. user ↔ group) according to policy. Endpoint stubbed; semantics and implementation planned. |
| **Revocation with propagation** | When a memory is sealed or revoked, propagate that to derived impacts/seeds so downstream context stays consistent. Not yet implemented. |

See **[app/memoryscope/README.md](app/memoryscope/README.md)** for v2 architecture and current status.

## Deployment notes

- Run migrations on the target database before or at deploy.
- Set production env vars (e.g. `DATABASE_URL`) via your platform; do not commit `.env`.
- CORS: set `CORS_ORIGINS` for your frontend if needed.

## Project layout (relevant to API)

- **app/** – FastAPI app, v1 and v2 routes, DB, config.
- **app/memoryscope/** – v2 core types, policy engine, v2 API.
- **alembic/** – Migrations.
- **tests/** – Pytest suite.
- **test_app/** – Optional test runner and demos using the API.
- **scripts/** – backup/restore and push-to-GitHub helper.
- **env.example** – Example environment variables; copy to `.env` and never commit `.env`.

## Makefile (optional)

```bash
make setup   # Copy env.example to .env
make up      # docker compose up -d
make migrate # alembic upgrade head
make test    # pytest
make all    # setup, up, migrate, test
```

## License and support

Use this API as the backend for your own products. Ensure you keep API keys and secrets out of version control and follow your own security and compliance requirements.
