"""Tests for Firebase authentication."""
import pytest
import os
from unittest.mock import patch, MagicMock
from fastapi import status
from fastapi.testclient import TestClient

from app.main import app
from app.firebase_auth import (
    initialize_firebase_admin,
    verify_id_token,
    is_firebase_initialized,
)


class TestFirebaseAuth:
    """Test suite for Firebase authentication."""

    def test_verify_firebase_token_missing_header(self, client):
        """Test that missing authorization header is rejected."""
        response = client.get(
            "/api/v1/console/apps",
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_verify_firebase_token_invalid_format(self, client):
        """Test that invalid authorization header format is rejected."""
        response = client.get(
            "/api/v1/console/apps",
            headers={"Authorization": "InvalidFormat token123"},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Invalid authorization header" in response.json()["detail"]

    def test_verify_firebase_token_missing_token(self, client):
        """Test that missing token in Bearer format is rejected."""
        response = client.get(
            "/api/v1/console/apps",
            headers={"Authorization": "Bearer "},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Missing token" in response.json()["detail"]

    @patch.dict(os.environ, {"FIREBASE_TEST_MODE": "true", "FIREBASE_TEST_USER_ID": "test_user_123"})
    def test_verify_firebase_token_test_mode(self, client):
        """Test that test mode allows test user ID when enabled."""
        response = client.get(
            "/api/v1/console/apps",
            headers={"Authorization": "Bearer test_user_123"},
        )
        # Should not return 401 (test mode enabled)
        # May return 200 or other status depending on Firebase initialization
        assert response.status_code != status.HTTP_401_UNAUTHORIZED

    @patch.dict(os.environ, {"FIREBASE_TEST_MODE": "false"}, clear=False)
    def test_verify_firebase_token_test_mode_disabled(self, client):
        """Test that test mode is disabled by default."""
        response = client.get(
            "/api/v1/console/apps",
            headers={"Authorization": "Bearer test_user_jonmoore"},
        )
        # Should reject test user ID when test mode is disabled
        # Will return 401 or 503 depending on Firebase initialization
        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_503_SERVICE_UNAVAILABLE,
        ]

    def test_verify_firebase_token_invalid_token(self, client):
        """Test that invalid token is rejected."""
        response = client.get(
            "/api/v1/console/apps",
            headers={"Authorization": "Bearer invalid_token_12345"},
        )
        # Should return 401 or 503 depending on Firebase initialization
        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_503_SERVICE_UNAVAILABLE,
        ]

    @patch("app.firebase_auth.auth")
    @patch("app.firebase_auth.is_firebase_initialized")
    def test_verify_id_token_success(self, mock_initialized, mock_auth):
        """Test successful token verification."""
        mock_initialized.return_value = True
        mock_auth.verify_id_token.return_value = {"uid": "user123", "email": "user@example.com"}
        
        # Patch auth module in firebase_auth
        with patch("app.firebase_auth.auth", mock_auth):
            result = verify_id_token("valid_token")
            assert result["uid"] == "user123"
            mock_auth.verify_id_token.assert_called_once_with("valid_token", check_revoked=True)

    @patch("app.firebase_auth.is_firebase_initialized")
    def test_verify_id_token_expired(self, mock_initialized):
        """Test expired token handling."""
        # Create mock exception that matches Firebase's exception structure
        class ExpiredIdTokenError(Exception):
            pass
        
        mock_initialized.return_value = True
        mock_auth = MagicMock()
        mock_auth.ExpiredIdTokenError = ExpiredIdTokenError
        mock_auth.verify_id_token.side_effect = ExpiredIdTokenError("Token expired")
        
        with patch("app.firebase_auth.auth", mock_auth):
            with pytest.raises(ValueError, match="Token expired"):
                verify_id_token("expired_token")

    @patch("app.firebase_auth.is_firebase_initialized")
    def test_verify_id_token_revoked(self, mock_initialized):
        """Test revoked token handling."""
        class RevokedIdTokenError(Exception):
            pass
        
        mock_initialized.return_value = True
        mock_auth = MagicMock()
        mock_auth.RevokedIdTokenError = RevokedIdTokenError
        mock_auth.verify_id_token.side_effect = RevokedIdTokenError("Token revoked")
        
        with patch("app.firebase_auth.auth", mock_auth):
            with pytest.raises(ValueError, match="Token revoked"):
                verify_id_token("revoked_token")

    @patch("app.firebase_auth.is_firebase_initialized")
    def test_verify_id_token_invalid(self, mock_initialized):
        """Test invalid token handling."""
        class InvalidIdTokenError(Exception):
            pass
        
        mock_initialized.return_value = True
        mock_auth = MagicMock()
        mock_auth.InvalidIdTokenError = InvalidIdTokenError
        mock_auth.verify_id_token.side_effect = InvalidIdTokenError("Invalid token")
        
        with patch("app.firebase_auth.auth", mock_auth):
            with pytest.raises(ValueError, match="Invalid token"):
                verify_id_token("invalid_token")

    def test_verify_id_token_not_initialized(self):
        """Test that verification fails if Firebase is not initialized."""
        with patch("app.firebase_auth.is_firebase_initialized", return_value=False):
            with pytest.raises(ValueError, match="Firebase Admin SDK not initialized"):
                verify_id_token("any_token")

    def test_verify_id_token_firebase_not_available(self):
        """Test that verification fails if Firebase is not available."""
        with patch("app.firebase_auth.FIREBASE_AVAILABLE", False):
            with pytest.raises(ValueError, match="Firebase Admin SDK not available"):
                verify_id_token("any_token")

