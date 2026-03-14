"""Tests for Notification model and digest idempotency logic."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock


class TestNotificationModel:
    """Tests for the Notification SQLAlchemy model."""

    def test_notification_fields(self) -> None:
        from storage.models import Notification
        n = Notification(
            user_id=1,
            digest_id=5,
            type="DIGEST_READY",
            title="Your daily digest is ready",
            body="Tap to view",
            is_read=False,
        )
        assert n.user_id == 1
        assert n.digest_id == 5
        assert n.type == "DIGEST_READY"
        assert n.title == "Your daily digest is ready"
        assert n.body == "Tap to view"
        assert n.is_read is False
        assert n.read_at is None

    def test_notification_nullable_fields(self) -> None:
        from storage.models import Notification
        n = Notification(user_id=1, title="Test", is_read=False)
        assert n.digest_id is None
        assert n.body is None
        assert n.read_at is None

    def test_notification_mark_read(self) -> None:
        from storage.models import Notification
        n = Notification(user_id=1, title="Test", is_read=False)
        n.is_read = True
        n.read_at = datetime(2026, 2, 26, 12, 0, 0)
        assert n.is_read is True
        assert n.read_at == datetime(2026, 2, 26, 12, 0, 0)

    def test_user_has_notifications_relationship(self) -> None:
        from storage.models import User
        assert "notifications" in User.__mapper__.relationships

    def test_notification_types(self) -> None:
        from storage.models import Notification
        for t in ["DIGEST_READY", "URGENT_EVENT", "SYSTEM"]:
            n = Notification(user_id=1, title="Test", type=t, is_read=False)
            assert n.type == t


def _load_digest_module():
    """Load routers/digest.py by file path to avoid routers/__init__ (which imports stripe)."""
    import importlib.util
    import os
    spec = importlib.util.spec_from_file_location(
        "routers_digest",
        os.path.join(os.path.dirname(__file__), "..", "routers", "digest.py"),
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestDigestSerialization:
    """Tests for digest serialization helpers."""

    def _get_helpers(self):
        mod = _load_digest_module()
        return mod._serialize_digest, mod._serialize_digest_summary

    def test_serialize_digest(self) -> None:
        _serialize_digest, _ = self._get_helpers()
        from storage.models import Digest
        d = Digest(
            id=10,
            user_id=1,
            child_id=None,
            digest_date="2026-02-26",
            source="gmail",
            summary_md="# Hello",
            items_json='[{"source":"gmail","subject":"Test"}]',
            raw_json="{}",
        )
        d.created_at = datetime(2026, 2, 26, 12, 0, 0)
        result = _serialize_digest(d)
        assert result["id"] == 10
        assert result["digest_date"] == "2026-02-26"
        assert result["summary_md"] == "# Hello"
        assert len(result["items"]) == 1
        assert result["items"][0]["subject"] == "Test"

    def test_serialize_digest_summary(self) -> None:
        _, _serialize_digest_summary = self._get_helpers()
        from storage.models import Digest
        d = Digest(
            id=10,
            user_id=1,
            digest_date="2026-02-25",
            source="gmail",
            summary_md="# Yesterday digest with lots of content here to test truncation",
            items_json='[{"source":"gmail"},{"source":"pdf"}]',
            raw_json="{}",
        )
        d.created_at = datetime(2026, 2, 25, 6, 0, 0)
        result = _serialize_digest_summary(d)
        assert result["id"] == 10
        assert result["item_count"] == 2
        assert len(result["preview"]) <= 200
        assert "digest_date" in result


class TestCreateDigestNotification:
    """Tests for _create_digest_notification helper."""

    def _get_helper(self):
        mod = _load_digest_module()
        return mod._create_digest_notification

    def test_new_digest_notification_title(self) -> None:
        _create_digest_notification = self._get_helper()
        session = MagicMock()
        _create_digest_notification(session, user_id=1, digest_id=5, is_new=True)
        session.add.assert_called_once()
        notif = session.add.call_args[0][0]
        assert notif.title == "Your daily digest is ready"
        assert notif.type == "DIGEST_READY"
        assert notif.digest_id == 5

    def test_updated_digest_notification_title(self) -> None:
        _create_digest_notification = self._get_helper()
        session = MagicMock()
        _create_digest_notification(session, user_id=1, digest_id=5, is_new=False)
        notif = session.add.call_args[0][0]
        assert notif.title == "Your digest has been updated"
