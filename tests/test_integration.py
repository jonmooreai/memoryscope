"""Comprehensive integration tests for complete workflows."""
import pytest
from fastapi import status
from datetime import datetime, timedelta


class TestIntegration:
    """Test suite for complete integration scenarios."""

    def test_complete_workflow(self, client, api_key):
        """Test complete workflow: create -> read -> continue -> revoke."""
        # 1. Create memory
        create_response = client.post(
            "/memory",
            headers={"X-API-Key": api_key},
            json={
                "user_id": "user1",
                "scope": "preferences",
                "source": "explicit_user_input",
                "ttl_days": 30,
                "value_json": {"likes": ["coffee", "tea"], "dislikes": ["milk"]},
            },
        )
        assert create_response.status_code == status.HTTP_201_CREATED
        memory_id = create_response.json()["id"]
        assert memory_id is not None

        # 2. Read memory
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
        read_data = read_response.json()
        assert "summary_text" in read_data
        assert "summary_struct" in read_data
        assert "likes" in read_data["summary_struct"]
        assert "coffee" in str(read_data["summary_struct"]["likes"])
        revocation_token = read_data["revocation_token"]

        # 3. Continue read
        continue_response = client.post(
            "/memory/read/continue",
            headers={"X-API-Key": api_key},
            json={"revocation_token": revocation_token},
        )
        assert continue_response.status_code == status.HTTP_200_OK
        assert continue_response.json()["summary_text"] == read_data["summary_text"]

        # 4. Revoke
        revoke_response = client.post(
            "/memory/revoke",
            headers={"X-API-Key": api_key},
            json={"revocation_token": revocation_token},
        )
        assert revoke_response.status_code == status.HTTP_200_OK
        assert revoke_response.json()["revoked"] is True

        # 5. Verify continue fails after revoke
        continue_after_revoke = client.post(
            "/memory/read/continue",
            headers={"X-API-Key": api_key},
            json={"revocation_token": revocation_token},
        )
        assert continue_after_revoke.status_code == status.HTTP_403_FORBIDDEN

    def test_multi_user_multi_scope_workflow(self, client, api_key):
        """Test workflow with multiple users and scopes."""
        users = ["user1", "user2", "user3"]
        scopes = ["preferences", "constraints", "communication"]

        # Create memories for each user/scope combination
        for user_id in users:
            for scope in scopes:
                response = client.post(
                    "/memory",
                    headers={"X-API-Key": api_key},
                    json={
                        "user_id": user_id,
                        "scope": scope,
                        "source": "explicit_user_input",
                        "ttl_days": 30,
                        "value_json": {"key": f"value_{user_id}_{scope}"},
                    },
                )
                assert response.status_code == status.HTTP_201_CREATED

        # Read memories for each user/scope
        for user_id in users:
            for scope in scopes:
                # Use appropriate purpose for each scope
                purposes = {
                    "preferences": "generate content",
                    "constraints": "recommendation",
                    "communication": "notification delivery",
                }
                response = client.post(
                    "/memory/read",
                    headers={"X-API-Key": api_key},
                    json={
                        "user_id": user_id,
                        "scope": scope,
                        "purpose": purposes[scope],
                    },
                )
                assert response.status_code == status.HTTP_200_OK
                # Verify user isolation
                assert response.json()["summary_text"] != "No memories found."

    def test_domain_isolation_workflow(self, client, api_key):
        """Test complete workflow with domain isolation."""
        # Create memories in different domains
        domains = ["work", "personal", None]
        for domain in domains:
            payload = {
                "user_id": "user1",
                "scope": "preferences",
                "source": "explicit_user_input",
                "ttl_days": 30,
                "value_json": {"likes": [f"item_{domain or 'none'}"]},
            }
            if domain:
                payload["domain"] = domain

            response = client.post(
                "/memory",
                headers={"X-API-Key": api_key},
                json=payload,
            )
            assert response.status_code == status.HTTP_201_CREATED

        # Read each domain separately
        for domain in domains:
            read_payload = {
                "user_id": "user1",
                "scope": "preferences",
                "purpose": "generate content",
            }
            if domain:
                read_payload["domain"] = domain

            response = client.post(
                "/memory/read",
                headers={"X-API-Key": api_key},
                json=read_payload,
            )
            assert response.status_code == status.HTTP_200_OK
            # Each domain should have its own memory
            summary = response.json()["summary_struct"]
            assert f"item_{domain or 'none'}" in str(summary["likes"])

    def test_memory_merging_workflow(self, client, api_key):
        """Test workflow with multiple memories that get merged."""
        # Create multiple memories over time
        memories_data = [
            {"likes": ["coffee"], "dislikes": ["milk"]},
            {"likes": ["tea"], "dislikes": ["sugar"]},
            {"likes": ["juice"], "dislikes": []},
        ]

        for mem_data in memories_data:
            response = client.post(
                "/memory",
                headers={"X-API-Key": api_key},
                json={
                    "user_id": "user1",
                    "scope": "preferences",
                    "source": "explicit_user_input",
                    "ttl_days": 30,
                    "value_json": mem_data,
                },
            )
            assert response.status_code == status.HTTP_201_CREATED

        # Read and verify merge
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
        # Should have all likes merged
        assert len(summary["likes"]) == 3
        assert "coffee" in summary["likes"]
        assert "tea" in summary["likes"]
        assert "juice" in summary["likes"]
        # Should have all dislikes merged
        assert len(summary["dislikes"]) == 2
        assert "milk" in summary["dislikes"]
        assert "sugar" in summary["dislikes"]

    def test_max_age_days_workflow(self, client, api_key):
        """Test workflow with max_age_days filtering."""
        # Create memories
        for i in range(5):
            response = client.post(
                "/memory",
                headers={"X-API-Key": api_key},
                json={
                    "user_id": "user1",
                    "scope": "preferences",
                    "source": "explicit_user_input",
                    "ttl_days": 30,
                    "value_json": {"likes": [f"item{i}"]},
                },
            )
            assert response.status_code == status.HTTP_201_CREATED

        # Read with max_age_days = 1 (should find recent memories)
        read_response = client.post(
            "/memory/read",
            headers={"X-API-Key": api_key},
            json={
                "user_id": "user1",
                "scope": "preferences",
                "purpose": "generate content",
                "max_age_days": 1,
            },
        )
        assert read_response.status_code == status.HTTP_200_OK
        assert read_response.json()["summary_text"] != "No memories found."

    def test_policy_enforcement_workflow(self, client, api_key):
        """Test complete workflow with policy enforcement."""
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

        # Try to read with allowed purpose
        allowed_response = client.post(
            "/memory/read",
            headers={"X-API-Key": api_key},
            json={
                "user_id": "user1",
                "scope": "preferences",
                "purpose": "generate content",  # Allowed
            },
        )
        assert allowed_response.status_code == status.HTTP_200_OK

        # Try to read with denied purpose
        denied_response = client.post(
            "/memory/read",
            headers={"X-API-Key": api_key},
            json={
                "user_id": "user1",
                "scope": "preferences",
                "purpose": "schedule meeting",  # Denied
            },
        )
        assert denied_response.status_code == status.HTTP_403_FORBIDDEN

    def test_all_scopes_workflow(self, client, api_key):
        """Test workflow for all scopes."""
        scopes = ["preferences", "constraints", "communication", "accessibility", "schedule", "attention"]
        purposes = {
            "preferences": "generate content",
            "constraints": "recommendation",
            "communication": "notification delivery",
            "accessibility": "ui rendering",
            "schedule": "scheduling",
            "attention": "notification delivery",
        }

        for scope in scopes:
            # Create memory
            create_response = client.post(
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
            assert create_response.status_code == status.HTTP_201_CREATED

            # Read memory
            read_response = client.post(
                "/memory/read",
                headers={"X-API-Key": api_key},
                json={
                    "user_id": "user1",
                    "scope": scope,
                    "purpose": purposes[scope],
                },
            )
            assert read_response.status_code == status.HTTP_200_OK
            assert "summary_text" in read_response.json()

    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/healthz")
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"status": "ok"}

    def test_audit_trail_workflow(self, client, api_key, test_db):
        """Test that audit events are created correctly."""
        from app.models import AuditEvent

        # Create memory
        create_response = client.post(
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
        assert create_response.status_code == status.HTTP_201_CREATED

        # Read memory
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

        # Check audit events
        db = test_db()
        create_events = db.query(AuditEvent).filter(AuditEvent.event_type == "MEMORY_WRITE").all()
        read_events = db.query(AuditEvent).filter(AuditEvent.event_type == "MEMORY_READ").all()
        db.close()

        assert len(create_events) >= 1
        assert len(read_events) >= 1

        # Verify event details
        create_event = create_events[0]
        assert create_event.user_id == "user1"
        assert create_event.scope == "preferences"

        read_event = read_events[0]
        assert read_event.user_id == "user1"
        assert read_event.scope == "preferences"
        assert read_event.purpose_class == "content_generation"

