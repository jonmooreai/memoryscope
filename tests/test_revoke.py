"""Test revoke token behavior."""
import pytest
from fastapi import status


def test_revoke_token_success(client, api_key, app_id):
    """Test successful token revocation."""
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

    # Revoke
    revoke_response = client.post(
        "/memory/revoke",
        headers={"X-API-Key": api_key},
        json={"revocation_token": revocation_token},
    )
    assert revoke_response.status_code == status.HTTP_200_OK
    assert revoke_response.json()["revoked"] is True
    assert "revoked_at" in revoke_response.json()


def test_revoke_token_not_found(client, api_key, app_id):
    """Test revoking a non-existent token returns 404."""
    revoke_response = client.post(
        "/memory/revoke",
        headers={"X-API-Key": api_key},
        json={"revocation_token": "non-existent-token"},
    )
    assert revoke_response.status_code == status.HTTP_404_NOT_FOUND


def test_revoke_token_already_revoked(client, api_key, app_id):
    """Test revoking an already revoked token returns 404."""
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

    # Revoke first time
    revoke1 = client.post(
        "/memory/revoke",
        headers={"X-API-Key": api_key},
        json={"revocation_token": revocation_token},
    )
    assert revoke1.status_code == status.HTTP_200_OK

    # Try to revoke again
    revoke2 = client.post(
        "/memory/revoke",
        headers={"X-API-Key": api_key},
        json={"revocation_token": revocation_token},
    )
    assert revoke2.status_code == status.HTTP_404_NOT_FOUND


def test_revoke_token_different_app(client, api_key, app_id, test_db):
    """Test that tokens from different apps cannot be revoked."""
    from app.models import App
    from app.utils import hash_api_key
    import uuid

    # Create another app
    db = test_db()
    other_api_key = "other-api-key"
    other_app = App(
        id=uuid.uuid4(),
        name="Other App",
        api_key_hash=hash_api_key(other_api_key),
        user_id="test-user-id-2",
    )
    db.add(other_app)
    db.commit()
    db.close()

    # Create and read with first app
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

    # Try to revoke with different app - should fail
    revoke_response = client.post(
        "/memory/revoke",
        headers={"X-API-Key": other_api_key},
        json={"revocation_token": revocation_token},
    )
    assert revoke_response.status_code == status.HTTP_404_NOT_FOUND


def test_revoke_breaks_continue(client, api_key, app_id):
    """Test that revoking a token breaks the continue endpoint."""
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

    # Continue should work before revoking
    continue_response = client.post(
        "/memory/read/continue",
        headers={"X-API-Key": api_key},
        json={"revocation_token": revocation_token},
    )
    assert continue_response.status_code == status.HTTP_200_OK
    assert "summary_text" in continue_response.json()

    # Revoke the token
    revoke_response = client.post(
        "/memory/revoke",
        headers={"X-API-Key": api_key},
        json={"revocation_token": revocation_token},
    )
    assert revoke_response.status_code == status.HTTP_200_OK

    # Continue should now fail with 403 REVOKED
    continue_response_after_revoke = client.post(
        "/memory/read/continue",
        headers={"X-API-Key": api_key},
        json={"revocation_token": revocation_token},
    )
    assert continue_response_after_revoke.status_code == status.HTTP_403_FORBIDDEN
    assert continue_response_after_revoke.json()["detail"] == "REVOKED"

