"""Comprehensive tests for memory read/continue endpoint."""
import pytest
from fastapi import status
from datetime import datetime, timedelta


class TestMemoryReadContinue:
    """Test suite for POST /memory/read/continue endpoint."""

    def test_continue_read_basic(self, client, api_key):
        """Test basic continue read functionality."""
        # Create and read memory to get revocation token
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
        revocation_token = read_response.json()["revocation_token"]

        # Continue read
        continue_response = client.post(
            "/memory/read/continue",
            headers={"X-API-Key": api_key},
            json={"revocation_token": revocation_token},
        )
        assert continue_response.status_code == status.HTTP_200_OK
        assert "summary_text" in continue_response.json()
        assert "revocation_token" in continue_response.json()
        assert continue_response.json()["revocation_token"] == revocation_token

    def test_continue_read_same_result(self, client, api_key):
        """Test that continue read returns same result as original read."""
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

        # Initial read
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
        original_summary = read_response.json()["summary_text"]
        original_struct = read_response.json()["summary_struct"]
        revocation_token = read_response.json()["revocation_token"]

        # Continue read
        continue_response = client.post(
            "/memory/read/continue",
            headers={"X-API-Key": api_key},
            json={"revocation_token": revocation_token},
        )
        assert continue_response.status_code == status.HTTP_200_OK
        continue_summary = continue_response.json()["summary_text"]
        continue_struct = continue_response.json()["summary_struct"]

        # Should return same result
        assert continue_summary == original_summary
        assert continue_struct == original_struct

    def test_continue_read_multiple_times(self, client, api_key):
        """Test that continue read can be called multiple times."""
        # Create and read memory
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

        read_response = client.post(
            "/memory/read",
            headers={"X-API-Key": api_key},
            json={
                "user_id": "user1",
                "scope": "preferences",
                "purpose": "generate content",
            },
        )
        revocation_token = read_response.json()["revocation_token"]

        # Continue read multiple times
        for _ in range(3):
            continue_response = client.post(
                "/memory/read/continue",
                headers={"X-API-Key": api_key},
                json={"revocation_token": revocation_token},
            )
            assert continue_response.status_code == status.HTTP_200_OK

    def test_continue_read_with_max_age_days(self, client, api_key):
        """Test continue read with max_age_days override."""
        # Create and read memory
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

        read_response = client.post(
            "/memory/read",
            headers={"X-API-Key": api_key},
            json={
                "user_id": "user1",
                "scope": "preferences",
                "purpose": "generate content",
                "max_age_days": 7,
            },
        )
        revocation_token = read_response.json()["revocation_token"]

        # Continue with different max_age_days
        continue_response = client.post(
            "/memory/read/continue",
            headers={"X-API-Key": api_key},
            json={
                "revocation_token": revocation_token,
                "max_age_days": 1,
            },
        )
        assert continue_response.status_code == status.HTTP_200_OK

    def test_continue_read_invalid_token(self, client, api_key):
        """Test continue read with invalid revocation token."""
        response = client.post(
            "/memory/read/continue",
            headers={"X-API-Key": api_key},
            json={"revocation_token": "invalid-token-123"},
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in response.json()["detail"].lower()

    def test_continue_read_revoked_token(self, client, api_key):
        """Test that continue read fails after token is revoked."""
        # Create and read memory
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

        read_response = client.post(
            "/memory/read",
            headers={"X-API-Key": api_key},
            json={
                "user_id": "user1",
                "scope": "preferences",
                "purpose": "generate content",
            },
        )
        revocation_token = read_response.json()["revocation_token"]

        # Revoke token
        revoke_response = client.post(
            "/memory/revoke",
            headers={"X-API-Key": api_key},
            json={"revocation_token": revocation_token},
        )
        assert revoke_response.status_code == status.HTTP_200_OK

        # Try to continue read - should fail
        continue_response = client.post(
            "/memory/read/continue",
            headers={"X-API-Key": api_key},
            json={"revocation_token": revocation_token},
        )
        assert continue_response.status_code == status.HTTP_403_FORBIDDEN
        assert continue_response.json()["detail"] == "REVOKED"

    def test_continue_read_expired_token(self, client, api_key, test_db):
        """Test that continue read fails with expired token."""
        from app.models import ReadGrant
        from datetime import datetime, timedelta

        # Create and read memory
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

        read_response = client.post(
            "/memory/read",
            headers={"X-API-Key": api_key},
            json={
                "user_id": "user1",
                "scope": "preferences",
                "purpose": "generate content",
            },
        )
        revocation_token = read_response.json()["revocation_token"]

        # Manually expire the grant in database
        db = test_db()
        from app.utils import hash_revocation_token
        token_hash = hash_revocation_token(revocation_token)
        grant = db.query(ReadGrant).filter(ReadGrant.revocation_token_hash == token_hash).first()
        if grant:
            grant.expires_at = datetime.utcnow() - timedelta(hours=1)  # Expired 1 hour ago
            db.commit()
        db.close()

        # Try to continue read - should fail
        continue_response = client.post(
            "/memory/read/continue",
            headers={"X-API-Key": api_key},
            json={"revocation_token": revocation_token},
        )
        assert continue_response.status_code == status.HTTP_403_FORBIDDEN
        assert continue_response.json()["detail"] == "REVOKED"

    def test_continue_read_different_app(self, client, api_key, test_db):
        """Test that continue read fails with token from different app."""
        from app.models import App
        from app.utils import hash_api_key
        import uuid

        # Create another app
        db = test_db()
        other_api_key = "other-api-key-789"
        other_app = App(
            id=uuid.uuid4(),
            name="Other App",
            api_key_hash=hash_api_key(other_api_key),
            user_id="test-user-id-2",
        )
        db.add(other_app)
        db.commit()
        db.close()

        # Create and read memory with first app
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

        read_response = client.post(
            "/memory/read",
            headers={"X-API-Key": api_key},
            json={
                "user_id": "user1",
                "scope": "preferences",
                "purpose": "generate content",
            },
        )
        revocation_token = read_response.json()["revocation_token"]

        # Try to continue read with different app - should fail
        continue_response = client.post(
            "/memory/read/continue",
            headers={"X-API-Key": other_api_key},
            json={"revocation_token": revocation_token},
        )
        assert continue_response.status_code == status.HTTP_404_NOT_FOUND

    def test_continue_read_missing_token(self, client, api_key):
        """Test continue read with missing revocation token."""
        response = client.post(
            "/memory/read/continue",
            headers={"X-API-Key": api_key},
            json={},
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_continue_read_new_memories_after_grant(self, client, api_key):
        """Test that continue read includes new memories created after grant."""
        # Create initial memory and read
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

        read_response = client.post(
            "/memory/read",
            headers={"X-API-Key": api_key},
            json={
                "user_id": "user1",
                "scope": "preferences",
                "purpose": "generate content",
            },
        )
        revocation_token = read_response.json()["revocation_token"]
        original_likes_count = len(read_response.json()["summary_struct"]["likes"])

        # Create new memory
        client.post(
            "/memory",
            headers={"X-API-Key": api_key},
            json={
                "user_id": "user1",
                "scope": "preferences",
                "source": "explicit_user_input",
                "ttl_days": 30,
                "value_json": {"likes": ["tea"]},
            },
        )

        # Continue read - should include new memory
        continue_response = client.post(
            "/memory/read/continue",
            headers={"X-API-Key": api_key},
            json={"revocation_token": revocation_token},
        )
        assert continue_response.status_code == status.HTTP_200_OK
        new_likes_count = len(continue_response.json()["summary_struct"]["likes"])
        assert new_likes_count > original_likes_count

