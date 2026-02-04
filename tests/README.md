# API Test Suite

This directory contains comprehensive automated tests for the Memory Scope API.

## Test Structure

The test suite is organized into the following modules:

### Core Endpoint Tests

- **test_memory_create.py** - Tests for POST `/memory` endpoint
  - Basic memory creation
  - All scopes and value shapes
  - Domain handling
  - TTL validation
  - Normalization
  - Edge cases

- **test_memory_read.py** - Tests for POST `/memory/read` endpoint
  - Basic reading
  - Domain filtering
  - Max age days filtering
  - Memory merging
  - Policy enforcement
  - User/scope/app isolation
  - Expired memory exclusion

- **test_memory_read_continue.py** - Tests for POST `/memory/read/continue` endpoint
  - Basic continue functionality
  - Token validation
  - Revocation handling
  - Expiration handling
  - App isolation

- **test_revoke.py** - Tests for POST `/memory/revoke` endpoint
  - Token revocation
  - Revocation validation
  - Cross-app isolation

### Functional Tests

- **test_authentication.py** - Authentication and authorization tests
  - API key validation
  - Missing/invalid keys
  - App isolation
  - All endpoints require auth

- **test_policy.py** - Policy enforcement tests
  - Scope-purpose combinations
  - Policy denial
  - Policy allowance

- **test_normalization.py** - Value normalization tests
  - All value shapes
  - Deduplication
  - Case handling
  - Sorting

- **test_deterministic_summary.py** - Deterministic merge tests
  - All scopes
  - Deterministic output
  - Summary structure validation

### Integration & Edge Cases

- **test_integration.py** - Complete workflow tests
  - End-to-end workflows
  - Multi-user scenarios
  - Domain isolation workflows
  - Memory merging workflows
  - Audit trail verification

- **test_edge_cases.py** - Edge case and error handling tests
  - Unicode characters
  - Special characters
  - Large values
  - Concurrent requests
  - Malformed input
  - Boundary conditions

## Running Tests

### Run All Tests

```bash
pytest tests/
```

### Run Specific Test File

```bash
pytest tests/test_memory_create.py
```

### Run Specific Test Class

```bash
pytest tests/test_memory_create.py::TestMemoryCreate
```

### Run Specific Test Method

```bash
pytest tests/test_memory_create.py::TestMemoryCreate::test_create_memory_basic
```

### Run with Verbose Output

```bash
pytest tests/ -v
```

### Run with Coverage

```bash
pytest tests/ --cov=app --cov-report=html
```

### Run in Parallel

```bash
pytest tests/ -n auto
```

## Test Configuration

Tests use a separate test database configured via `DATABASE_URL_TEST` environment variable or by appending `_test` to the main database name.

The test database is:
- Created fresh for each test session
- Migrated using Alembic
- Cleaned between tests (not between test sessions)

## Test Fixtures

Key fixtures available in `conftest.py`:

- `test_db_engine` - Database engine for test session
- `test_db` - Database session for each test
- `test_app` - Test app with API key
- `client` - FastAPI test client
- `api_key` - API key string for test app
- `app_id` - App ID for test app

## Test Coverage

The test suite covers:

✅ All API endpoints
✅ All scopes (preferences, constraints, communication, accessibility, schedule, attention)
✅ All value shapes (kv_map, likes_dislikes, rules_list, schedule_windows, boolean_flags, attention_settings)
✅ Authentication and authorization
✅ Policy enforcement
✅ Domain isolation
✅ User isolation
✅ App isolation
✅ Memory merging
✅ Normalization
✅ TTL and expiration
✅ Revocation tokens
✅ Edge cases and error handling
✅ Integration workflows
✅ Audit trail

## Adding New Tests

When adding new tests:

1. Follow the existing test structure and naming conventions
2. Use appropriate fixtures from `conftest.py`
3. Test both success and failure cases
4. Include edge cases and boundary conditions
5. Verify isolation between users, scopes, domains, and apps
6. Test normalization and deterministic behavior where applicable

## Continuous Integration

These tests should be run:
- Before committing code
- In CI/CD pipeline
- Before deploying to production

