# MemoryScope Core API v2.2 Implementation

This package implements the MemoryScope Core API specification (PRD v2.2).

## Architecture

### Core Components

1. **Core Types** (`core_types.py`)
   - Canonical MemoryObject schema
   - Truth modes, memory states, ownership models
   - Constraint schemas
   - Access log entries
   - ThoughtPatternArtifact (spiral detection)

2. **Policy Engine** (`policy_engine.py`)
   - YAML-based policy DSL parser
   - Deterministic rule evaluation
   - Policy trace generation
   - Support for ingest, query, and tool execution evaluation

3. **V2 API** (`v2_api.py`)
   - RESTful endpoints following PRD v2.2
   - Policy enforcement integration
   - Access logging

## Key Features Implemented

### ✅ Completed

- [x] Core type definitions (MemoryObject, constraints, etc.)
- [x] Policy engine with DSL parser
- [x] V2 API endpoint structure
- [x] Basic policy evaluation (ingest, query, tool execution)
- [x] Demo script for testing

### 🚧 In Progress / TODO

- [ ] Database schema migration for v2 memories
- [ ] Memory storage and retrieval implementation
- [ ] Spiral detection engine
- [ ] Impact extraction and constraint merging
- [ ] Retrieval engine with sealed memory filtering
- [ ] Reconstruction engine
- [ ] Full observability (explain, replay)

## Usage

### Creating a Memory

```python
from app.memoryscope.core_types import MemoryObject, MemoryType, TruthMode, Scope, Temporal, Content, Ownership, Provenance

memory = MemoryObject(
    id="mem_abc123",
    tenant_id="t_demo",
    scope=Scope(scope_type="user", scope_id="u_123"),
    type=MemoryType.EVENT,
    truth_mode=TruthMode.FACTUAL_CLAIM,
    ownership=Ownership(
        owner_type="user",
        owners=["u_123"],
        claimant="u_123",
        subjects=["u_123"],
    ),
    temporal=Temporal(
        occurred_at_observed=datetime.utcnow(),
        time_precision="exact",
        time_confidence=1.0,
    ),
    content=Content(format="text", text="I had a great day"),
    provenance=Provenance(source="user", confidence=0.9),
)
```

### Policy Evaluation

```python
from app.memoryscope.policy_engine import PolicyEngine

engine = PolicyEngine()

# Evaluate ingest
result = engine.evaluate_ingest(memory)
print(f"State: {result['state']}")
print(f"Derive impacts: {result['derive_impacts']}")
print(f"Policy trace: {result['trace']}")
```

### API Usage

See `test_app/v2_demo.py` for examples of using the v2 API endpoints.

## Policy DSL

The policy engine supports YAML-based policies:

```yaml
policy_version: pol_2026_01_06_01
defaults:
  write: allow
  read: deny
  include_in_prompt: deny

rules:
  - id: seal_sensitive_events
    when:
      memory.type: event
      memory.sensitivity.categories: [trauma, shame, moral_injury]
    then:
      set_state: sealed
      allow_read: false
      include_in_prompt: false
```

## Safety Guarantees

The implementation follows PRD v2.2 safety requirements:

1. **Sealed memories never returned** - Sealed events are filtered out in query results
2. **Truth mode enforcement** - Counterfactual/imagined memories cannot be used for tool execution
3. **Disputed facts suppressed** - Disputed factual claims are not returned in chat responses
4. **Deterministic evaluation** - Policy decisions are deterministic and traceable

## Next Steps

1. Implement database storage for v2 memories
2. Complete retrieval engine with proper filtering
3. Implement spiral detection
4. Add reconstruction engine
5. Complete observability endpoints

