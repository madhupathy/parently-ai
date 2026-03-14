"""Tests for entitlement enforcement logic."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from storage.models import User, UserEntitlement


class TestCheckDigestEntitlement:
    """Tests for check_digest_entitlement dependency."""

    def _make_user(self, user_id: int = 1) -> User:
        user = User(email="test@example.com", name="Test", provider="google")
        user.id = user_id
        return user

    @patch("dependencies.get_db")
    def test_premium_user_allowed(self, mock_get_db: MagicMock) -> None:
        from dependencies import check_digest_entitlement

        user = self._make_user()
        ent = UserEntitlement(user_id=1, plan="PREMIUM", premium_active=True, digests_remaining=0)

        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value.first.return_value = ent
        mock_get_db.return_value.session_scope.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_get_db.return_value.session_scope.return_value.__exit__ = MagicMock(return_value=False)

        result = check_digest_entitlement(current_user=user)
        assert result.email == "test@example.com"

    @patch("dependencies.get_db")
    def test_free_user_with_remaining_allowed(self, mock_get_db: MagicMock) -> None:
        from dependencies import check_digest_entitlement

        user = self._make_user()
        ent = UserEntitlement(user_id=1, plan="FREE", premium_active=False, digests_remaining=100)

        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value.first.return_value = ent
        mock_get_db.return_value.session_scope.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_get_db.return_value.session_scope.return_value.__exit__ = MagicMock(return_value=False)

        result = check_digest_entitlement(current_user=user)
        assert result.email == "test@example.com"

    @patch("dependencies.get_db")
    def test_free_user_exhausted_raises_402(self, mock_get_db: MagicMock) -> None:
        from dependencies import check_digest_entitlement

        user = self._make_user()
        ent = UserEntitlement(user_id=1, plan="FREE", premium_active=False, digests_remaining=0)

        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value.first.return_value = ent
        mock_get_db.return_value.session_scope.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_get_db.return_value.session_scope.return_value.__exit__ = MagicMock(return_value=False)

        with pytest.raises(HTTPException) as exc_info:
            check_digest_entitlement(current_user=user)
        assert exc_info.value.status_code == 402
        assert "free_limit_reached" in str(exc_info.value.detail)

    @patch("dependencies.get_db")
    def test_no_entitlement_creates_one(self, mock_get_db: MagicMock) -> None:
        from dependencies import check_digest_entitlement

        user = self._make_user()

        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value.first.return_value = None
        mock_get_db.return_value.session_scope.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_get_db.return_value.session_scope.return_value.__exit__ = MagicMock(return_value=False)

        result = check_digest_entitlement(current_user=user)
        assert result.email == "test@example.com"
        mock_session.add.assert_called_once()
        mock_session.flush.assert_called_once()
