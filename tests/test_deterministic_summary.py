"""Test deterministic summary output."""
import pytest
from fastapi import status
from datetime import datetime, timedelta


def test_deterministic_summary_preferences(client, api_key, app_id):
    """Test deterministic summary for preferences scope."""
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

    # Read twice - should get same result
    read1 = client.post(
        "/memory/read",
        headers={"X-API-Key": api_key},
        json={
            "user_id": "user1",
            "scope": "preferences",
            "purpose": "generate content",
        },
    )
    read2 = client.post(
        "/memory/read",
        headers={"X-API-Key": api_key},
        json={
            "user_id": "user1",
            "scope": "preferences",
            "purpose": "generate content",
        },
    )

    assert read1.status_code == status.HTTP_200_OK
    assert read2.status_code == status.HTTP_200_OK

    # Should be identical (deterministic)
    assert read1.json()["summary_text"] == read2.json()["summary_text"]
    assert read1.json()["summary_struct"] == read2.json()["summary_struct"]
    assert read1.json()["confidence"] == read2.json()["confidence"]


def test_deterministic_summary_constraints(client, api_key, app_id):
    """Test deterministic summary for constraints scope."""
    # Create memories
    client.post(
        "/memory",
        headers={"X-API-Key": api_key},
        json={
            "user_id": "user1",
            "scope": "constraints",
            "source": "explicit_user_input",
            "ttl_days": 30,
            "value_json": ["rule1", "rule2"],
        },
    )

    read_response = client.post(
        "/memory/read",
        headers={"X-API-Key": api_key},
        json={
            "user_id": "user1",
            "scope": "constraints",
            "purpose": "recommendation",
        },
    )

    assert read_response.status_code == status.HTTP_200_OK
    summary = read_response.json()
    assert "summary_text" in summary
    assert len(summary["summary_text"]) <= 240
    assert "summary_struct" in summary
    assert "confidence" in summary
    assert 0.0 <= summary["confidence"] <= 1.0


def test_deterministic_summary_schedule(client, api_key, app_id):
    """Test deterministic summary for schedule scope."""
    client.post(
        "/memory",
        headers={"X-API-Key": api_key},
        json={
            "user_id": "user1",
            "scope": "schedule",
            "source": "explicit_user_input",
            "ttl_days": 30,
            "value_json": [
                {"start": "09:00", "end": "17:00", "day": "weekday"},
            ],
        },
    )

    read_response = client.post(
        "/memory/read",
        headers={"X-API-Key": api_key},
        json={
            "user_id": "user1",
            "scope": "schedule",
            "purpose": "scheduling",
        },
    )

    assert read_response.status_code == status.HTTP_200_OK
    summary = read_response.json()
    assert "windows" in summary["summary_struct"]


def test_deterministic_summary_communication(client, api_key, app_id):
    """Test deterministic summary for communication scope."""
    client.post(
        "/memory",
        headers={"X-API-Key": api_key},
        json={
            "user_id": "user1",
            "scope": "communication",
            "source": "explicit_user_input",
            "ttl_days": 30,
            "value_json": {"preferred_channel": "email"},
        },
    )

    read_response = client.post(
        "/memory/read",
        headers={"X-API-Key": api_key},
        json={
            "user_id": "user1",
            "scope": "communication",
            "purpose": "notification delivery",
        },
    )

    assert read_response.status_code == status.HTTP_200_OK
    summary = read_response.json()
    assert "preferences" in summary["summary_struct"]


def test_deterministic_summary_accessibility(client, api_key, app_id):
    """Test deterministic summary for accessibility scope."""
    client.post(
        "/memory",
        headers={"X-API-Key": api_key},
        json={
            "user_id": "user1",
            "scope": "accessibility",
            "source": "explicit_user_input",
            "ttl_days": 30,
            "value_json": {"high_contrast": True, "large_text": False},
        },
    )

    read_response = client.post(
        "/memory/read",
        headers={"X-API-Key": api_key},
        json={
            "user_id": "user1",
            "scope": "accessibility",
            "purpose": "ui rendering",
        },
    )

    assert read_response.status_code == status.HTTP_200_OK
    summary = read_response.json()
    assert "flags" in summary["summary_struct"] or "settings" in summary["summary_struct"]


def test_deterministic_summary_attention(client, api_key, app_id):
    """Test deterministic summary for attention scope."""
    client.post(
        "/memory",
        headers={"X-API-Key": api_key},
        json={
            "user_id": "user1",
            "scope": "attention",
            "source": "explicit_user_input",
            "ttl_days": 30,
            "value_json": {"focus_mode": True, "do_not_disturb": False},
        },
    )

    read_response = client.post(
        "/memory/read",
        headers={"X-API-Key": api_key},
        json={
            "user_id": "user1",
            "scope": "attention",
            "purpose": "notification delivery",
        },
    )

    assert read_response.status_code == status.HTTP_200_OK
    summary = read_response.json()
    assert "settings" in summary["summary_struct"]

