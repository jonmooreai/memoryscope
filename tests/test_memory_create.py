"""Comprehensive tests for memory creation endpoint."""
import pytest
from fastapi import status
from datetime import datetime, timedelta
from uuid import UUID


class TestMemoryCreate:
    """Test suite for POST /memory endpoint."""

    def test_create_memory_basic(self, client, api_key):
        """Test basic memory creation with minimal required fields."""
        response = client.post(
            "/memory",
            headers={"X-API-Key": api_key},
            json={
                "user_id": "user1",
                "scope": "preferences",
                "source": "explicit_user_input",
                "ttl_days": 30,
                "value_json": {"likes": ["coffee"]},
            },
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert "id" in data
        assert data["user_id"] == "user1"
        assert data["scope"] == "preferences"
        assert UUID(data["id"])  # Valid UUID
        assert "created_at" in data
        assert "expires_at" in data

    def test_create_memory_all_scopes(self, client, api_key):
        """Test memory creation for all allowed scopes."""
        scopes = ["preferences", "constraints", "communication", "accessibility", "schedule", "attention"]
        for scope in scopes:
            response = client.post(
                "/memory",
                headers={"X-API-Key": api_key},
                json={
                    "user_id": "user1",
                    "scope": scope,
                    "source": "explicit_user_input",
                    "ttl_days": 30,
                    "value_json": {"key": "value"},
                },
            )
            assert response.status_code == status.HTTP_201_CREATED, f"Failed for scope: {scope}"
            assert response.json()["scope"] == scope

    def test_create_memory_all_value_shapes(self, client, api_key):
        """Test memory creation with all supported value shapes."""
        test_cases = [
            # kv_map
            {"value_json": {"key1": "value1", "key2": 42}},
            # likes_dislikes
            {"value_json": {"likes": ["coffee", "tea"], "dislikes": ["milk"]}},
            # rules_list
            {"value_json": ["rule1", "rule2", "rule3"]},
            # schedule_windows (list)
            {"value_json": [{"start": "09:00", "end": "17:00", "day": "weekday"}]},
            # schedule_windows (dict)
            {"value_json": {"windows": [{"start": "09:00", "end": "17:00"}]}},
            # boolean_flags
            {"value_json": {"flag1": True, "flag2": False}},
            # attention_settings
            {"value_json": {"focus_mode": True, "do_not_disturb": False}},
        ]

        for i, test_case in enumerate(test_cases):
            response = client.post(
                "/memory",
                headers={"X-API-Key": api_key},
                json={
                    "user_id": f"user{i}",
                    "scope": "preferences",
                    "source": "explicit_user_input",
                    "ttl_days": 30,
                    **test_case,
                },
            )
            assert response.status_code == status.HTTP_201_CREATED, f"Failed for value_json: {test_case['value_json']}"

    def test_create_memory_with_domain(self, client, api_key):
        """Test memory creation with domain specified."""
        response = client.post(
            "/memory",
            headers={"X-API-Key": api_key},
            json={
                "user_id": "user1",
                "scope": "preferences",
                "domain": "work",
                "source": "explicit_user_input",
                "ttl_days": 30,
                "value_json": {"likes": ["coffee"]},
            },
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()["domain"] == "work"

    def test_create_memory_without_domain(self, client, api_key):
        """Test memory creation without domain (null domain)."""
        response = client.post(
            "/memory",
            headers={"X-API-Key": api_key},
            json={
                "user_id": "user1",
                "scope": "preferences",
                "source": "explicit_user_input",
                "ttl_days": 30,
                "value_json": {"likes": ["coffee"]},
            },
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        # Domain should be None/null when not provided
        assert data.get("domain") is None

    def test_create_memory_ttl_validation(self, client, api_key):
        """Test TTL validation (1-365 days)."""
        # Valid TTL
        response = client.post(
            "/memory",
            headers={"X-API-Key": api_key},
            json={
                "user_id": "user1",
                "scope": "preferences",
                "source": "explicit_user_input",
                "ttl_days": 1,
                "value_json": {"likes": ["coffee"]},
            },
        )
        assert response.status_code == status.HTTP_201_CREATED

        # Valid TTL (max)
        response = client.post(
            "/memory",
            headers={"X-API-Key": api_key},
            json={
                "user_id": "user1",
                "scope": "preferences",
                "source": "explicit_user_input",
                "ttl_days": 365,
                "value_json": {"likes": ["coffee"]},
            },
        )
        assert response.status_code == status.HTTP_201_CREATED

        # Invalid TTL (too low)
        response = client.post(
            "/memory",
            headers={"X-API-Key": api_key},
            json={
                "user_id": "user1",
                "scope": "preferences",
                "source": "explicit_user_input",
                "ttl_days": 0,
                "value_json": {"likes": ["coffee"]},
            },
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # Invalid TTL (too high)
        response = client.post(
            "/memory",
            headers={"X-API-Key": api_key},
            json={
                "user_id": "user1",
                "scope": "preferences",
                "source": "explicit_user_input",
                "ttl_days": 366,
                "value_json": {"likes": ["coffee"]},
            },
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_create_memory_expires_at_calculation(self, client, api_key):
        """Test that expires_at is correctly calculated from TTL."""
        ttl_days = 30
        response = client.post(
            "/memory",
            headers={"X-API-Key": api_key},
            json={
                "user_id": "user1",
                "scope": "preferences",
                "source": "explicit_user_input",
                "ttl_days": ttl_days,
                "value_json": {"likes": ["coffee"]},
            },
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        
        created_at = datetime.fromisoformat(data["created_at"].replace("Z", "+00:00"))
        expires_at = datetime.fromisoformat(data["expires_at"].replace("Z", "+00:00"))
        
        # Expires_at should be approximately TTL days after created_at
        delta = expires_at - created_at
        assert abs(delta.total_seconds() - (ttl_days * 24 * 3600)) < 60  # Within 1 minute tolerance

    def test_create_memory_invalid_scope(self, client, api_key):
        """Test memory creation with invalid scope."""
        response = client.post(
            "/memory",
            headers={"X-API-Key": api_key},
            json={
                "user_id": "user1",
                "scope": "invalid_scope",
                "source": "explicit_user_input",
                "ttl_days": 30,
                "value_json": {"likes": ["coffee"]},
            },
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_create_memory_invalid_source(self, client, api_key):
        """Test memory creation with invalid source."""
        response = client.post(
            "/memory",
            headers={"X-API-Key": api_key},
            json={
                "user_id": "user1",
                "scope": "preferences",
                "source": "invalid_source",
                "ttl_days": 30,
                "value_json": {"likes": ["coffee"]},
            },
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_create_memory_invalid_value_shape(self, client, api_key):
        """Test memory creation with value_json that doesn't match any shape."""
        # Empty list doesn't match any shape (rules_list requires at least one item)
        # Returns 422 from Pydantic validation
        response = client.post(
            "/memory",
            headers={"X-API-Key": api_key},
            json={
                "user_id": "user1",
                "scope": "constraints",
                "source": "explicit_user_input",
                "ttl_days": 30,
                "value_json": [],  # Empty list doesn't match any shape
            },
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        # Pydantic validation errors are in a different format
        detail = response.json()["detail"]
        if isinstance(detail, list):
            assert any("does not match any allowed shape" in str(item).lower() for item in detail)
        else:
            assert "does not match any allowed shape" in str(detail).lower()

    def test_create_memory_missing_required_fields(self, client, api_key):
        """Test memory creation with missing required fields."""
        # Missing user_id
        response = client.post(
            "/memory",
            headers={"X-API-Key": api_key},
            json={
                "scope": "preferences",
                "source": "explicit_user_input",
                "ttl_days": 30,
                "value_json": {"likes": ["coffee"]},
            },
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # Missing scope
        response = client.post(
            "/memory",
            headers={"X-API-Key": api_key},
            json={
                "user_id": "user1",
                "source": "explicit_user_input",
                "ttl_days": 30,
                "value_json": {"likes": ["coffee"]},
            },
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # Missing source
        response = client.post(
            "/memory",
            headers={"X-API-Key": api_key},
            json={
                "user_id": "user1",
                "scope": "preferences",
                "ttl_days": 30,
                "value_json": {"likes": ["coffee"]},
            },
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # Missing value_json
        response = client.post(
            "/memory",
            headers={"X-API-Key": api_key},
            json={
                "user_id": "user1",
                "scope": "preferences",
                "source": "explicit_user_input",
                "ttl_days": 30,
            },
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_create_memory_user_setting_source(self, client, api_key):
        """Test memory creation with user_setting source."""
        response = client.post(
            "/memory",
            headers={"X-API-Key": api_key},
            json={
                "user_id": "user1",
                "scope": "preferences",
                "source": "user_setting",
                "ttl_days": 30,
                "value_json": {"likes": ["coffee"]},
            },
        )
        assert response.status_code == status.HTTP_201_CREATED

    def test_create_memory_multiple_users(self, client, api_key):
        """Test memory creation for multiple users."""
        for i in range(5):
            response = client.post(
                "/memory",
                headers={"X-API-Key": api_key},
                json={
                    "user_id": f"user{i}",
                    "scope": "preferences",
                    "source": "explicit_user_input",
                    "ttl_days": 30,
                    "value_json": {"likes": [f"item{i}"]},
                },
            )
            assert response.status_code == status.HTTP_201_CREATED
            assert response.json()["user_id"] == f"user{i}"

    def test_create_memory_same_user_different_scopes(self, client, api_key):
        """Test creating memories for same user with different scopes."""
        scopes = ["preferences", "constraints", "communication"]
        for scope in scopes:
            response = client.post(
                "/memory",
                headers={"X-API-Key": api_key},
                json={
                    "user_id": "user1",
                    "scope": scope,
                    "source": "explicit_user_input",
                    "ttl_days": 30,
                    "value_json": {"key": "value"},
                },
            )
            assert response.status_code == status.HTTP_201_CREATED
            assert response.json()["scope"] == scope

    def test_create_memory_same_user_same_scope_different_domains(self, client, api_key):
        """Test creating memories for same user/scope with different domains."""
        domains = ["work", "personal", None]
        for domain in domains:
            payload = {
                "user_id": "user1",
                "scope": "preferences",
                "source": "explicit_user_input",
                "ttl_days": 30,
                "value_json": {"likes": ["coffee"]},
            }
            if domain is not None:
                payload["domain"] = domain
            
            response = client.post(
                "/memory",
                headers={"X-API-Key": api_key},
                json=payload,
            )
            assert response.status_code == status.HTTP_201_CREATED

    def test_create_memory_normalization_applied(self, client, api_key):
        """Test that normalization is applied during memory creation."""
        # Create memory with duplicates and case variations
        response = client.post(
            "/memory",
            headers={"X-API-Key": api_key},
            json={
                "user_id": "user1",
                "scope": "preferences",
                "source": "explicit_user_input",
                "ttl_days": 30,
                "value_json": {
                    "likes": ["coffee", "tea", "coffee", "Tea"],  # duplicates and case
                    "dislikes": ["milk", "MILK"],
                },
            },
        )
        assert response.status_code == status.HTTP_201_CREATED
        
        # Read back and verify normalization
        read_response = client.post(
            "/memory/read",
            headers={"X-API-Key": api_key},
            json={
                "user_id": "user1",
                "scope": "preferences",
                "purpose": "generate content",
            },
        )
        assert read_response.status_code == status.HTTP_200_OK
        summary = read_response.json()["summary_struct"]
        # Likes should be deduped (case-insensitive)
        assert len(summary["likes"]) <= 2  # coffee, tea (one of tea/Tea)
        # Should be sorted
        assert summary["likes"] == sorted(summary["likes"])

    def test_create_memory_empty_value_json(self, client, api_key):
        """Test memory creation with empty value_json structures."""
        # Empty dict is valid (matches boolean_flags shape)
        response = client.post(
            "/memory",
            headers={"X-API-Key": api_key},
            json={
                "user_id": "user1",
                "scope": "preferences",
                "source": "explicit_user_input",
                "ttl_days": 30,
                "value_json": {},
            },
        )
        assert response.status_code == status.HTTP_201_CREATED

        # Empty list is invalid (doesn't match any shape) - returns 422 from Pydantic validation
        response = client.post(
            "/memory",
            headers={"X-API-Key": api_key},
            json={
                "user_id": "user1",
                "scope": "constraints",
                "source": "explicit_user_input",
                "ttl_days": 30,
                "value_json": [],
            },
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert "does not match any allowed shape" in response.json()["detail"][0]["msg"].lower() or "does not match any allowed shape" in str(response.json()["detail"]).lower()

