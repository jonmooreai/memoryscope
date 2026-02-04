"""Test policy enforcement."""
import pytest
from fastapi import status

from app.schemas import POLICY_MATRIX


def test_policy_denial_preferences(client, api_key, app_id):
    """Test that preferences scope denies non-allowed purpose classes."""
    # Create a memory
    memory_response = client.post(
        "/memory",
        headers={"X-API-Key": api_key},
        json={
            "user_id": "user1",
            "scope": "preferences",
            "source": "explicit_user_input",
            "ttl_days": 30,
            "value_json": {"likes": ["coffee"], "dislikes": ["tea"]},
        },
    )
    assert memory_response.status_code == status.HTTP_201_CREATED

    # Try to read with disallowed purpose (scheduling)
    read_response = client.post(
        "/memory/read",
        headers={"X-API-Key": api_key},
        json={
            "user_id": "user1",
            "scope": "preferences",
            "purpose": "schedule meeting",
        },
    )
    assert read_response.status_code == status.HTTP_403_FORBIDDEN
    assert "not allowed" in read_response.json()["detail"].lower()


def test_policy_denial_constraints(client, api_key, app_id):
    """Test that constraints scope denies non-allowed purpose classes."""
    # Create a memory
    memory_response = client.post(
        "/memory",
        headers={"X-API-Key": api_key},
        json={
            "user_id": "user1",
            "scope": "constraints",
            "source": "explicit_user_input",
            "ttl_days": 30,
            "value_json": {"max_budget": 1000},
        },
    )
    assert memory_response.status_code == status.HTTP_201_CREATED

    # Try to read with disallowed purpose (content_generation)
    read_response = client.post(
        "/memory/read",
        headers={"X-API-Key": api_key},
        json={
            "user_id": "user1",
            "scope": "constraints",
            "purpose": "generate content",
        },
    )
    assert read_response.status_code == status.HTTP_403_FORBIDDEN


def test_policy_allows_correct_purpose(client, api_key, app_id):
    """Test that allowed purpose classes work."""
    # Create a memory
    memory_response = client.post(
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
    assert memory_response.status_code == status.HTTP_201_CREATED

    # Read with allowed purpose (content_generation)
    read_response = client.post(
        "/memory/read",
        headers={"X-API-Key": api_key},
        json={
            "user_id": "user1",
            "scope": "preferences",
            "purpose": "generate personalized content",
        },
    )
    assert read_response.status_code == status.HTTP_200_OK
    assert "summary_text" in read_response.json()


def test_all_policy_combinations():
    """Test that all policy combinations are correctly defined."""
    for scope, allowed_purposes in POLICY_MATRIX.items():
        assert len(allowed_purposes) > 0, f"Scope {scope} has no allowed purposes"
        for purpose in allowed_purposes:
            assert purpose in {
                "content_generation",
                "recommendation",
                "scheduling",
                "ui_rendering",
                "notification_delivery",
                "task_execution",
            }, f"Invalid purpose class: {purpose}"

