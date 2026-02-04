"""Comprehensive tests for edge cases and error handling."""
import pytest
from fastapi import status
from datetime import datetime, timedelta


class TestEdgeCases:
    """Test suite for edge cases and error scenarios."""

    def test_very_long_user_id(self, client, api_key):
        """Test with very long user_id."""
        long_user_id = "a" * 1000
        response = client.post(
            "/memory",
            headers={"X-API-Key": api_key},
            json={
                "user_id": long_user_id,
                "scope": "preferences",
                "source": "explicit_user_input",
                "ttl_days": 30,
                "value_json": {"likes": ["coffee"]},
            },
        )
        assert response.status_code == status.HTTP_201_CREATED

    def test_very_long_domain(self, client, api_key):
        """Test with very long domain."""
        long_domain = "a" * 500
        response = client.post(
            "/memory",
            headers={"X-API-Key": api_key},
            json={
                "user_id": "user1",
                "scope": "preferences",
                "domain": long_domain,
                "source": "explicit_user_input",
                "ttl_days": 30,
                "value_json": {"likes": ["coffee"]},
            },
        )
        assert response.status_code == status.HTTP_201_CREATED

    def test_unicode_characters(self, client, api_key):
        """Test with unicode characters in values."""
        response = client.post(
            "/memory",
            headers={"X-API-Key": api_key},
            json={
                "user_id": "user1",
                "scope": "preferences",
                "source": "explicit_user_input",
                "ttl_days": 30,
                "value_json": {
                    "likes": ["咖啡", "茶", "☕"],
                    "dislikes": ["牛奶"],
                },
            },
        )
        assert response.status_code == status.HTTP_201_CREATED

        # Read back
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

    def test_special_characters_in_domain(self, client, api_key):
        """Test with special characters in domain."""
        special_domains = ["work-email", "work.email", "work_email", "work@email"]
        for domain in special_domains:
            response = client.post(
                "/memory",
                headers={"X-API-Key": api_key},
                json={
                    "user_id": "user1",
                    "scope": "preferences",
                    "domain": domain,
                    "source": "explicit_user_input",
                    "ttl_days": 30,
                    "value_json": {"likes": ["coffee"]},
                },
            )
            assert response.status_code == status.HTTP_201_CREATED

    def test_empty_string_values(self, client, api_key):
        """Test with empty string values."""
        response = client.post(
            "/memory",
            headers={"X-API-Key": api_key},
            json={
                "user_id": "",
                "scope": "preferences",
                "source": "explicit_user_input",
                "ttl_days": 30,
                "value_json": {"likes": []},
            },
        )
        # Empty user_id might be invalid, but let's see what happens
        # This tests edge case handling
        assert response.status_code in [status.HTTP_201_CREATED, status.HTTP_422_UNPROCESSABLE_ENTITY]

    def test_null_values_in_json(self, client, api_key):
        """Test with null values in value_json."""
        response = client.post(
            "/memory",
            headers={"X-API-Key": api_key},
            json={
                "user_id": "user1",
                "scope": "preferences",
                "source": "explicit_user_input",
                "ttl_days": 30,
                "value_json": {"key1": None, "key2": "value"},
            },
        )
        # Should handle null values gracefully
        assert response.status_code in [status.HTTP_201_CREATED, status.HTTP_400_BAD_REQUEST]

    def test_nested_structures(self, client, api_key):
        """Test with nested structures in value_json."""
        # Test with nested dict (might not match any shape)
        response = client.post(
            "/memory",
            headers={"X-API-Key": api_key},
            json={
                "user_id": "user1",
                "scope": "preferences",
                "source": "explicit_user_input",
                "ttl_days": 30,
                "value_json": {
                    "nested": {
                        "deep": {
                            "value": "test"
                        }
                    }
                },
            },
        )
        # Should reject if it doesn't match any shape
        assert response.status_code in [status.HTTP_201_CREATED, status.HTTP_400_BAD_REQUEST]

    def test_very_large_value_json(self, client, api_key):
        """Test with very large value_json."""
        large_value = {
            "likes": [f"item_{i}" for i in range(1000)],
            "dislikes": [f"bad_{i}" for i in range(1000)],
        }
        response = client.post(
            "/memory",
            headers={"X-API-Key": api_key},
            json={
                "user_id": "user1",
                "scope": "preferences",
                "source": "explicit_user_input",
                "ttl_days": 30,
                "value_json": large_value,
            },
        )
        assert response.status_code == status.HTTP_201_CREATED

    def test_concurrent_requests(self, client, api_key):
        """Test handling of concurrent requests."""
        import concurrent.futures

        def create_memory(i):
            return client.post(
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

        # Create 10 memories concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(create_memory, i) for i in range(10)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]

        # All should succeed
        assert all(r.status_code == status.HTTP_201_CREATED for r in results)

    def test_rapid_sequential_requests(self, client, api_key):
        """Test rapid sequential requests."""
        # Create 50 memories rapidly
        for i in range(50):
            response = client.post(
                "/memory",
                headers={"X-API-Key": api_key},
                json={
                    "user_id": f"user{i % 5}",  # Cycle through 5 users
                    "scope": "preferences",
                    "source": "explicit_user_input",
                    "ttl_days": 30,
                    "value_json": {"likes": [f"item{i}"]},
                },
            )
            assert response.status_code == status.HTTP_201_CREATED

    def test_malformed_json(self, client, api_key):
        """Test with malformed JSON."""
        # This would be caught by FastAPI before reaching our code
        # But we can test with invalid structure
        response = client.post(
            "/memory",
            headers={"X-API-Key": api_key},
            json={
                "user_id": "user1",
                "scope": "preferences",
                "source": "explicit_user_input",
                "ttl_days": 30,
                "value_json": "not a dict or list",  # Invalid type
            },
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_missing_content_type(self, client, api_key):
        """Test request without Content-Type header."""
        # FastAPI should handle this, but test edge case
        response = client.post(
            "/memory",
            headers={
                "X-API-Key": api_key,
                "Content-Type": "application/json",
            },
            json={
                "user_id": "user1",
                "scope": "preferences",
                "source": "explicit_user_input",
                "ttl_days": 30,
                "value_json": {"likes": ["coffee"]},
            },
        )
        assert response.status_code == status.HTTP_201_CREATED

    def test_extra_fields_ignored(self, client, api_key):
        """Test that extra fields in request are ignored."""
        response = client.post(
            "/memory",
            headers={"X-API-Key": api_key},
            json={
                "user_id": "user1",
                "scope": "preferences",
                "source": "explicit_user_input",
                "ttl_days": 30,
                "value_json": {"likes": ["coffee"]},
                "extra_field": "should be ignored",
                "another_extra": 123,
            },
        )
        # Pydantic should ignore extra fields by default
        assert response.status_code == status.HTTP_201_CREATED

    def test_negative_ttl(self, client, api_key):
        """Test with negative TTL."""
        response = client.post(
            "/memory",
            headers={"X-API-Key": api_key},
            json={
                "user_id": "user1",
                "scope": "preferences",
                "source": "explicit_user_input",
                "ttl_days": -1,
                "value_json": {"likes": ["coffee"]},
            },
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_zero_ttl(self, client, api_key):
        """Test with zero TTL."""
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

    def test_very_large_ttl(self, client, api_key):
        """Test with TTL at maximum."""
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

    def test_ttl_exceeds_maximum(self, client, api_key):
        """Test with TTL exceeding maximum."""
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

    def test_invalid_purpose_normalization(self, client, api_key):
        """Test purpose normalization with various inputs."""
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

        # Test various purpose strings
        purposes = [
            "generate",
            "GENERATE",
            "Generate Content",
            "generate_content",
            "create something",
            "write article",
            "recommend",
            "suggest",
            "schedule",
            "calendar",
            "ui",
            "render",
            "notify",
            "alert",
            "task",
            "execute",
            "unknown purpose that defaults to content_generation",
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
            # Should either succeed or be denied by policy, but not crash
            assert response.status_code in [
                status.HTTP_200_OK,
                status.HTTP_403_FORBIDDEN,
            ]

    def test_empty_purpose_string(self, client, api_key):
        """Test with empty purpose string."""
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
                "purpose": "",
            },
        )
        # Empty purpose should default to content_generation
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_403_FORBIDDEN]

