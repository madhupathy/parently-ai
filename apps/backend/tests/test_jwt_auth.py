"""Tests for JWT authentication and entitlement enforcement."""

from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

import jwt
import pytest
from fastapi import HTTPException

from dependencies import _decode_jwt, check_digest_entitlement, get_current_user, verify_cron_secret


SECRET = "test-secret-key-for-jwt"


def _mint_jwt(email: str = "test@example.com", name: str = "Test User", provider: str = "google", exp_offset: int = 3600) -> str:
    """Helper to mint a test JWT."""
    payload = {
        "email": email,
        "name": name,
        "provider": provider,
        "iat": int(time.time()),
        "exp": int(time.time()) + exp_offset,
    }
    return jwt.encode(payload, SECRET, algorithm="HS256")


class TestDecodeJWT:
    """Tests for _decode_jwt."""

    @patch("dependencies.get_settings")
    def test_valid_token(self, mock_settings: MagicMock) -> None:
        mock_settings.return_value.nextauth_secret = SECRET
        token = _mint_jwt()
        payload = _decode_jwt(token)
        assert payload["email"] == "test@example.com"
        assert payload["name"] == "Test User"
        assert payload["provider"] == "google"

    @patch("dependencies.get_settings")
    def test_expired_token_raises_401(self, mock_settings: MagicMock) -> None:
        mock_settings.return_value.nextauth_secret = SECRET
        token = _mint_jwt(exp_offset=-10)  # already expired
        with pytest.raises(HTTPException) as exc_info:
            _decode_jwt(token)
        assert exc_info.value.status_code == 401
        assert "expired" in str(exc_info.value.detail).lower()

    @patch("dependencies.get_settings")
    def test_wrong_secret_raises_401(self, mock_settings: MagicMock) -> None:
        mock_settings.return_value.nextauth_secret = "wrong-secret"
        token = _mint_jwt()
        with pytest.raises(HTTPException) as exc_info:
            _decode_jwt(token)
        assert exc_info.value.status_code == 401

    @patch("dependencies.get_settings")
    def test_malformed_token_raises_401(self, mock_settings: MagicMock) -> None:
        mock_settings.return_value.nextauth_secret = SECRET
        with pytest.raises(HTTPException) as exc_info:
            _decode_jwt("not.a.valid.jwt")
        assert exc_info.value.status_code == 401


class TestVerifyCronSecret:
    """Tests for verify_cron_secret."""

    @patch("dependencies.get_settings")
    def test_valid_cron_secret(self, mock_settings: MagicMock) -> None:
        mock_settings.return_value.cron_secret = "my-cron-secret"
        result = verify_cron_secret("my-cron-secret")
        assert result == "my-cron-secret"

    @patch("dependencies.get_settings")
    def test_invalid_cron_secret_raises_401(self, mock_settings: MagicMock) -> None:
        mock_settings.return_value.cron_secret = "my-cron-secret"
        with pytest.raises(HTTPException) as exc_info:
            verify_cron_secret("wrong-secret")
        assert exc_info.value.status_code == 401

    @patch("dependencies.get_settings")
    def test_no_cron_secret_configured_raises_401(self, mock_settings: MagicMock) -> None:
        mock_settings.return_value.cron_secret = None
        with pytest.raises(HTTPException) as exc_info:
            verify_cron_secret("any-value")
        assert exc_info.value.status_code == 401
