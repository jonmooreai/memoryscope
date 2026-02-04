"""Test normalization of values."""
import pytest
from fastapi import status

from app.utils import normalize_value_json


def test_normalize_likes_dislikes():
    """Test normalization of likes/dislikes arrays."""
    value = {
        "likes": ["coffee", "tea", "coffee", "Tea"],  # duplicates and case
        "dislikes": ["milk", "MILK", "sugar"],
    }
    normalized = normalize_value_json(value, "likes_dislikes")
    # Case-insensitive dedupe: "tea" and "Tea" become one item (first occurrence kept)
    assert len(normalized["likes"]) == 2  # coffee, tea (one of tea/Tea)
    assert "coffee" in normalized["likes"]
    assert any("tea" in item.lower() for item in normalized["likes"])
    # Dislikes: milk and MILK become one
    assert len(normalized["dislikes"]) == 2  # milk (one of milk/MILK), sugar
    assert "sugar" in normalized["dislikes"]


def test_normalize_rules_list():
    """Test normalization of rules_list."""
    value = ["rule1", "rule2", "rule1", "rule3"]
    normalized = normalize_value_json(value, "rules_list")
    assert normalized == ["rule1", "rule2", "rule3"]  # sorted, deduped


def test_normalize_boolean_flags():
    """Test normalization of boolean_flags (lowercase keys)."""
    value = {"EnableFeature": True, "DisableOther": False}
    normalized = normalize_value_json(value, "boolean_flags")
    assert normalized == {"enablefeature": True, "disableother": False}


def test_normalize_attention_settings(client, api_key, app_id):
    """Test normalization of attention_settings."""
    value = {
        "FocusMode": "enabled",
        "Tags": ["WORK", "urgent"],
        "DoNotDisturb": True,
    }
    normalized = normalize_value_json(value, "attention_settings")
    assert normalized["focusmode"] == "enabled"
    assert normalized["tags"] == ["work", "urgent"]  # lowercase
    assert normalized["donotdisturb"] is True


def test_normalize_in_memory_creation(client, api_key, app_id):
    """Test that normalization happens during memory creation."""
    response = client.post(
        "/memory",
        headers={"X-API-Key": api_key},
        json={
            "user_id": "user1",
            "scope": "preferences",
            "source": "explicit_user_input",
            "ttl_days": 30,
            "value_json": {
                "likes": ["coffee", "tea", "coffee"],
                "dislikes": ["milk"],
            },
        },
    )
    assert response.status_code == status.HTTP_201_CREATED

    # Verify normalization by reading back
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
    # Check that likes are deduped and sorted
    if "likes" in summary:
        assert len(summary["likes"]) == 2  # coffee, tea (deduped)
        assert summary["likes"] == sorted(summary["likes"])

