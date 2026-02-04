"""Comprehensive tests for memory read endpoint."""
import pytest
from fastapi import status
from datetime import datetime, timedelta


class TestMemoryRead:
    """Test suite for POST /memory/read endpoint."""

    def test_read_memory_no_memories(self, client, api_key):
        """Test reading when no memories exist."""
        response = client.post(
            "/memory/read",
            headers={"X-API-Key": api_key},
            json={
                "user_id": "user1",
                "scope": "preferences",
                "purpose": "generate content",
            },
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "summary_text" in data
        assert data["summary_text"] == "No memories found."
        assert "summary_struct" in data
        assert data["confidence"] == 0.0
        assert "revocation_token" in data
        assert "expires_at" in data

    def test_read_memory_basic(self, client, api_key):
        """Test basic memory read."""
        # Create memory
        client.post(
            "/memory",
            headers={"X-API-Key": api_key},
            json={
                "user_id": "user1",
                "scope": "preferences",
                "source": "explicit_user_input",
                "ttl_days": 30,
                "value_json": {"likes": ["coffee", "tea"]},
            },
        )

        # Read memory
        response = client.post(
            "/memory/read",
            headers={"X-API-Key": api_key},
            json={
                "user_id": "user1",
                "scope": "preferences",
                "purpose": "generate content",
            },
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "summary_text" in data
        assert len(data["summary_text"]) <= 240
        assert "summary_struct" in data
        assert "confidence" in data
        assert 0.0 <= data["confidence"] <= 1.0
        assert "revocation_token" in data
        assert "expires_at" in data

    def test_read_memory_with_domain(self, client, api_key):
        """Test reading memory with domain filter."""
        # Create memory with domain
        client.post(
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

        # Read with matching domain
        response = client.post(
            "/memory/read",
            headers={"X-API-Key": api_key},
            json={
                "user_id": "user1",
                "scope": "preferences",
                "domain": "work",
                "purpose": "generate content",
            },
        )
        assert response.status_code == status.HTTP_200_OK
        assert "summary_text" in response.json()

        # Read without domain (should not find domain-specific memory)
        response = client.post(
            "/memory/read",
            headers={"X-API-Key": api_key},
            json={
                "user_id": "user1",
                "scope": "preferences",
                "purpose": "generate content",
            },
        )
        assert response.status_code == status.HTTP_200_OK
        # Should return "No memories found" since domain doesn't match
        assert response.json()["summary_text"] == "No memories found."

    def test_read_memory_domain_isolation(self, client, api_key):
        """Test that memories with different domains are isolated."""
        # Create memories with different domains
        client.post(
            "/memory",
            headers={"X-API-Key": api_key},
            json={
                "user_id": "user1",
                "scope": "preferences",
                "domain": "work",
                "source": "explicit_user_input",
                "ttl_days": 30,
                "value_json": {"likes": ["work_coffee"]},
            },
        )
        client.post(
            "/memory",
            headers={"X-API-Key": api_key},
            json={
                "user_id": "user1",
                "scope": "preferences",
                "domain": "personal",
                "source": "explicit_user_input",
                "ttl_days": 30,
                "value_json": {"likes": ["personal_tea"]},
            },
        )

        # Read work domain
        response = client.post(
            "/memory/read",
            headers={"X-API-Key": api_key},
            json={
                "user_id": "user1",
                "scope": "preferences",
                "domain": "work",
                "purpose": "generate content",
            },
        )
        assert response.status_code == status.HTTP_200_OK
        summary = response.json()["summary_struct"]
        assert "work_coffee" in str(summary["likes"])

        # Read personal domain
        response = client.post(
            "/memory/read",
            headers={"X-API-Key": api_key},
            json={
                "user_id": "user1",
                "scope": "preferences",
                "domain": "personal",
                "purpose": "generate content",
            },
        )
        assert response.status_code == status.HTTP_200_OK
        summary = response.json()["summary_struct"]
        assert "personal_tea" in str(summary["likes"])

    def test_read_memory_max_age_days(self, client, api_key):
        """Test reading memory with max_age_days filter."""
        # Create old memory (simulated by creating with short TTL and waiting)
        # For testing, we'll create a memory and use max_age_days to filter
        client.post(
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

        # Read with max_age_days = 1 (should find recent memory)
        response = client.post(
            "/memory/read",
            headers={"X-API-Key": api_key},
            json={
                "user_id": "user1",
                "scope": "preferences",
                "purpose": "generate content",
                "max_age_days": 1,
            },
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["summary_text"] != "No memories found."

        # Read with max_age_days = 0 (should not find any memory)
        response = client.post(
            "/memory/read",
            headers={"X-API-Key": api_key},
            json={
                "user_id": "user1",
                "scope": "preferences",
                "purpose": "generate content",
                "max_age_days": 0,
            },
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY  # Invalid max_age_days

    def test_read_memory_merges_multiple_memories(self, client, api_key):
        """Test that reading merges multiple memories correctly."""
        # Create multiple memories
        for i in range(3):
            client.post(
                "/memory",
                headers={"X-API-Key": api_key},
                json={
                    "user_id": "user1",
                    "scope": "preferences",
                    "source": "explicit_user_input",
                    "ttl_days": 30,
                    "value_json": {
                        "likes": [f"item{i}"],
                        "dislikes": [f"bad{i}"],
                    },
                },
            )

        # Read and verify merge
        response = client.post(
            "/memory/read",
            headers={"X-API-Key": api_key},
            json={
                "user_id": "user1",
                "scope": "preferences",
                "purpose": "generate content",
            },
        )
        assert response.status_code == status.HTTP_200_OK
        summary = response.json()["summary_struct"]
        # Should have merged all likes and dislikes
        assert len(summary["likes"]) == 3
        assert len(summary["dislikes"]) == 3

    def test_read_memory_all_purpose_classes(self, client, api_key):
        """Test reading with all valid purpose classes."""
        # Create memory
        client.post(
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

        # Test all purpose keywords that map to allowed purpose classes
        purposes = [
            "generate content",  # content_generation
            "recommend something",  # recommendation
            "schedule meeting",  # scheduling
            "render ui",  # ui_rendering
            "send notification",  # notification_delivery
            "execute task",  # task_execution
        ]

        for purpose in purposes:
            response = client.post(
                "/memory/read",
                headers={"X-API-Key": api_key},
                json={
                    "user_id": "user1",
                    "scope": "preferences",
                    "purpose": purpose,
                },
            )
            # Some may be denied by policy, but request should be valid
            assert response.status_code in [status.HTTP_200_OK, status.HTTP_403_FORBIDDEN]

    def test_read_memory_policy_enforcement(self, client, api_key):
        """Test that policy correctly allows/denies access."""
        # Create memory in preferences scope
        client.post(
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

        # Allowed purpose (content_generation)
        response = client.post(
            "/memory/read",
            headers={"X-API-Key": api_key},
            json={
                "user_id": "user1",
                "scope": "preferences",
                "purpose": "generate content",
            },
        )
        assert response.status_code == status.HTTP_200_OK

        # Denied purpose (scheduling)
        response = client.post(
            "/memory/read",
            headers={"X-API-Key": api_key},
            json={
                "user_id": "user1",
                "scope": "preferences",
                "purpose": "schedule meeting",
            },
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "not allowed" in response.json()["detail"].lower()

    def test_read_memory_revocation_token_format(self, client, api_key):
        """Test that revocation token is returned in correct format."""
        client.post(
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

        response = client.post(
            "/memory/read",
            headers={"X-API-Key": api_key},
            json={
                "user_id": "user1",
                "scope": "preferences",
                "purpose": "generate content",
            },
        )
        assert response.status_code == status.HTTP_200_OK
        token = response.json()["revocation_token"]
        # Should be a UUID string
        assert isinstance(token, str)
        assert len(token) > 0

    def test_read_memory_expires_at_format(self, client, api_key):
        """Test that expires_at is in correct format."""
        client.post(
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

        response = client.post(
            "/memory/read",
            headers={"X-API-Key": api_key},
            json={
                "user_id": "user1",
                "scope": "preferences",
                "purpose": "generate content",
            },
        )
        assert response.status_code == status.HTTP_200_OK
        expires_at_str = response.json()["expires_at"]
        # Should be parseable as datetime
        expires_at = datetime.fromisoformat(expires_at_str.replace("Z", "+00:00"))
        assert expires_at > datetime.utcnow()

    def test_read_memory_user_isolation(self, client, api_key):
        """Test that users cannot read each other's memories."""
        # Create memory for user1
        client.post(
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

        # Try to read as user2
        response = client.post(
            "/memory/read",
            headers={"X-API-Key": api_key},
            json={
                "user_id": "user2",
                "scope": "preferences",
                "purpose": "generate content",
            },
        )
        assert response.status_code == status.HTTP_200_OK
        # Should return "No memories found" for different user
        assert response.json()["summary_text"] == "No memories found."

    def test_read_memory_scope_isolation(self, client, api_key):
        """Test that memories are isolated by scope."""
        # Create memory in preferences scope
        client.post(
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

        # Try to read from constraints scope
        response = client.post(
            "/memory/read",
            headers={"X-API-Key": api_key},
            json={
                "user_id": "user1",
                "scope": "constraints",
                "purpose": "recommendation",
            },
        )
        assert response.status_code == status.HTTP_200_OK
        # Should return "No memories found" for different scope
        assert response.json()["summary_text"] == "No memories found."

    def test_read_memory_app_isolation(self, client, api_key, test_db):
        """Test that apps cannot read each other's memories."""
        from app.models import App
        from app.utils import hash_api_key
        import uuid

        # Create another app
        db = test_db()
        other_api_key = "other-api-key-456"
        other_app = App(
            id=uuid.uuid4(),
            name="Other App",
            api_key_hash=hash_api_key(other_api_key),
            user_id="test-user-id-2",
        )
        db.add(other_app)
        db.commit()
        db.close()

        # Create memory with first app
        client.post(
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

        # Try to read with other app
        response = client.post(
            "/memory/read",
            headers={"X-API-Key": other_api_key},
            json={
                "user_id": "user1",
                "scope": "preferences",
                "purpose": "generate content",
            },
        )
        assert response.status_code == status.HTTP_200_OK
        # Should return "No memories found" since memories are app-scoped
        assert response.json()["summary_text"] == "No memories found."

    def test_read_memory_expired_memories_excluded(self, client, api_key, test_db, app_id):
        """Test that expired memories are not included in reads."""
        from app.models import Memory
        from datetime import datetime, timedelta

        # Create a memory with very short TTL
        db = test_db()
        memory = Memory(
            user_id="user1",
            scope="preferences",
            value_json={"likes": ["coffee"]},
            value_shape="likes_dislikes",
            source="explicit_user_input",
            ttl_days=1,
            created_at=datetime.utcnow() - timedelta(days=2),  # Created 2 days ago
            expires_at=datetime.utcnow() - timedelta(days=1),  # Expired 1 day ago
            app_id=app_id,
        )
        db.add(memory)
        db.commit()
        db.close()

        # Try to read - should not find expired memory
        response = client.post(
            "/memory/read",
            headers={"X-API-Key": api_key},
            json={
                "user_id": "user1",
                "scope": "preferences",
                "purpose": "generate content",
            },
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["summary_text"] == "No memories found."

    def test_read_memory_summary_text_length(self, client, api_key):
        """Test that summary_text respects max length."""
        # Create many memories to potentially exceed length
        for i in range(10):
            client.post(
                "/memory",
                headers={"X-API-Key": api_key},
                json={
                    "user_id": "user1",
                    "scope": "preferences",
                    "source": "explicit_user_input",
                    "ttl_days": 30,
                    "value_json": {
                        "likes": [f"item_{i}_" * 10],  # Long strings
                    },
                },
            )

        response = client.post(
            "/memory/read",
            headers={"X-API-Key": api_key},
            json={
                "user_id": "user1",
                "scope": "preferences",
                "purpose": "generate content",
            },
        )
        assert response.status_code == status.HTTP_200_OK
        summary_text = response.json()["summary_text"]
        assert len(summary_text) <= 240

    def test_read_memory_confidence_range(self, client, api_key):
        """Test that confidence is always in valid range."""
        # Create memory
        client.post(
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

        response = client.post(
            "/memory/read",
            headers={"X-API-Key": api_key},
            json={
                "user_id": "user1",
                "scope": "preferences",
                "purpose": "generate content",
            },
        )
        assert response.status_code == status.HTTP_200_OK
        confidence = response.json()["confidence"]
        assert 0.0 <= confidence <= 1.0

    def test_read_memory_invalid_scope(self, client, api_key):
        """Test reading with invalid scope."""
        response = client.post(
            "/memory/read",
            headers={"X-API-Key": api_key},
            json={
                "user_id": "user1",
                "scope": "invalid_scope",
                "purpose": "generate content",
            },
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_read_memory_missing_required_fields(self, client, api_key):
        """Test reading with missing required fields."""
        # Missing user_id
        response = client.post(
            "/memory/read",
            headers={"X-API-Key": api_key},
            json={
                "scope": "preferences",
                "purpose": "generate content",
            },
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # Missing scope
        response = client.post(
            "/memory/read",
            headers={"X-API-Key": api_key},
            json={
                "user_id": "user1",
                "purpose": "generate content",
            },
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # Missing purpose
        response = client.post(
            "/memory/read",
            headers={"X-API-Key": api_key},
            json={
                "user_id": "user1",
                "scope": "preferences",
            },
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

