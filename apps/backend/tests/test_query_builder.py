"""Tests for gmail_query_builder and new models."""

from __future__ import annotations

from datetime import datetime
from typing import Optional


class _ChildStub:
    """Lightweight stand-in for Child used by tests."""
    def __init__(self, name: str, school_name: Optional[str] = None, teacher_name: Optional[str] = None):
        self.name = name
        self.school_name = school_name
        self.teacher_name = teacher_name


class _ProfileStub:
    """Lightweight stand-in for ChildSearchProfile used by tests."""
    def __init__(
        self,
        gmail_query_base: Optional[str] = None,
        subject_keywords_json: Optional[str] = None,
        sender_allowlist_json: Optional[str] = None,
        sender_blocklist_json: Optional[str] = None,
        label_whitelist_json: Optional[str] = None,
        exclude_keywords_json: Optional[str] = None,
    ):
        self.gmail_query_base = gmail_query_base
        self.subject_keywords_json = subject_keywords_json
        self.sender_allowlist_json = sender_allowlist_json
        self.sender_blocklist_json = sender_blocklist_json
        self.label_whitelist_json = label_whitelist_json
        self.exclude_keywords_json = exclude_keywords_json
        self.last_sync_at = None

    def subject_keywords(self):
        import json
        return json.loads(self.subject_keywords_json) if self.subject_keywords_json else []

    def sender_allowlist(self):
        import json
        return json.loads(self.sender_allowlist_json) if self.sender_allowlist_json else []

    def sender_blocklist(self):
        import json
        return json.loads(self.sender_blocklist_json) if self.sender_blocklist_json else []

    def label_whitelist(self):
        import json
        return json.loads(self.label_whitelist_json) if self.label_whitelist_json else []

    def exclude_keywords(self):
        import json
        return json.loads(self.exclude_keywords_json) if self.exclude_keywords_json else []


class TestBuildGmailQuery:
    """Tests for build_gmail_query."""

    def test_basic_child_name_only(self) -> None:
        from services.gmail_query_builder import build_gmail_query
        child = _ChildStub(name="Vrinda")
        query = build_gmail_query(child, profile=None, lookback_days=14)
        assert "newer_than:14d" in query
        assert "Vrinda" in query
        assert "-category:promotions" in query

    def test_child_with_school_and_teacher(self) -> None:
        from services.gmail_query_builder import build_gmail_query
        child = _ChildStub(name="Emma", school_name="Cedar Ridge Elementary", teacher_name="Ms Johnson")
        query = build_gmail_query(child, profile=None, lookback_days=7)
        assert "newer_than:7d" in query
        assert "Emma" in query
        assert '"Cedar Ridge Elementary"' in query
        assert '"Ms Johnson"' in query

    def test_child_with_multiple_teachers(self) -> None:
        from services.gmail_query_builder import build_gmail_query
        child = _ChildStub(name="Kai", teacher_name="Ms Johnson, Mr Patel")
        query = build_gmail_query(child, profile=None)
        assert '"Ms Johnson"' in query
        assert '"Mr Patel"' in query

    def test_profile_with_subject_keywords(self) -> None:
        from services.gmail_query_builder import build_gmail_query
        child = _ChildStub(name="Vrinda")
        profile = _ProfileStub(subject_keywords_json='["field trip", "permission slip"]')
        query = build_gmail_query(child, profile=profile)
        assert '"field trip"' in query
        assert '"permission slip"' in query

    def test_profile_with_sender_allowlist(self) -> None:
        from services.gmail_query_builder import build_gmail_query
        child = _ChildStub(name="Vrinda")
        profile = _ProfileStub(sender_allowlist_json='["@classdojo.com", "@brightwheel.com"]')
        query = build_gmail_query(child, profile=profile)
        assert "from:@classdojo.com" in query
        assert "from:@brightwheel.com" in query

    def test_profile_with_label_whitelist(self) -> None:
        from services.gmail_query_builder import build_gmail_query
        child = _ChildStub(name="Vrinda")
        profile = _ProfileStub(label_whitelist_json='["School"]')
        query = build_gmail_query(child, profile=profile)
        assert "label:School" in query

    def test_profile_with_exclude_keywords(self) -> None:
        from services.gmail_query_builder import build_gmail_query
        child = _ChildStub(name="Vrinda")
        profile = _ProfileStub(exclude_keywords_json='["sale", "promo"]')
        query = build_gmail_query(child, profile=profile)
        assert "-sale" in query or '-"sale"' in query
        assert "-promo" in query or '-"promo"' in query

    def test_profile_with_sender_blocklist(self) -> None:
        from services.gmail_query_builder import build_gmail_query
        child = _ChildStub(name="Vrinda")
        profile = _ProfileStub(sender_blocklist_json='["spam@example.com"]')
        query = build_gmail_query(child, profile=profile)
        assert "-from:spam@example.com" in query

    def test_gmail_query_base_override(self) -> None:
        from services.gmail_query_builder import build_gmail_query
        child = _ChildStub(name="Vrinda")
        profile = _ProfileStub(gmail_query_base="label:School newer_than:30d")
        query = build_gmail_query(child, profile=profile)
        assert query == "label:School newer_than:30d"

    def test_gmail_query_base_override_with_since(self) -> None:
        from services.gmail_query_builder import build_gmail_query
        child = _ChildStub(name="Vrinda")
        profile = _ProfileStub(gmail_query_base="label:School")
        ts = datetime(2026, 2, 20, 12, 0, 0)
        query = build_gmail_query(child, profile=profile, since_timestamp=ts)
        assert "label:School" in query
        assert "after:" in query

    def test_incremental_since_timestamp(self) -> None:
        from services.gmail_query_builder import build_gmail_query
        child = _ChildStub(name="Vrinda")
        ts = datetime(2026, 2, 20, 12, 0, 0)
        query = build_gmail_query(child, profile=None, since_timestamp=ts)
        assert "after:" in query
        assert "newer_than" not in query


class TestBuildDefaultBroadQuery:
    """Tests for build_default_broad_query."""

    def test_default_broad(self) -> None:
        from services.gmail_query_builder import build_default_broad_query
        query = build_default_broad_query(lookback_days=30)
        assert "newer_than:30d" in query
        assert "school" in query.lower()
        assert "-category:promotions" in query

    def test_custom_lookback(self) -> None:
        from services.gmail_query_builder import build_default_broad_query
        query = build_default_broad_query(lookback_days=7)
        assert "newer_than:7d" in query


class TestNewModels:
    """Tests for ChildSearchProfile and GmailMessageIndex models."""

    def test_search_profile_model(self) -> None:
        from storage.models import ChildSearchProfile
        p = ChildSearchProfile(
            child_id=1,
            subject_keywords_json='["field trip"]',
            sender_allowlist_json='["@school.com"]',
        )
        assert p.child_id == 1
        assert p.subject_keywords() == ["field trip"]
        assert p.sender_allowlist() == ["@school.com"]
        assert p.sender_blocklist() == []
        assert p.label_whitelist() == []
        assert p.exclude_keywords() == []

    def test_search_profile_empty_json(self) -> None:
        from storage.models import ChildSearchProfile
        p = ChildSearchProfile(child_id=1)
        assert p.subject_keywords() == []
        assert p.sender_allowlist() == []

    def test_gmail_message_index_model(self) -> None:
        from storage.models import GmailMessageIndex
        m = GmailMessageIndex(
            user_id=1,
            child_id=2,
            gmail_message_id="abc123",
            thread_id="thread456",
            from_email="teacher@school.com",
            subject="Field Trip Permission",
            snippet="Please sign...",
            label_ids_json='["INBOX", "IMPORTANT"]',
            matched_rules_json='{"sender": "@school.com"}',
        )
        assert m.gmail_message_id == "abc123"
        assert m.label_ids() == ["INBOX", "IMPORTANT"]
        assert m.matched_rules() == {"sender": "@school.com"}

    def test_gmail_message_index_empty_json(self) -> None:
        from storage.models import GmailMessageIndex
        m = GmailMessageIndex(
            user_id=1,
            gmail_message_id="xyz",
        )
        assert m.label_ids() == []
        assert m.matched_rules() == {}

    def test_document_new_fields(self) -> None:
        from storage.models import Document
        d = Document(
            user_id=1,
            child_id=3,
            source_type="email",
            source_id="msg_123",
            filename="email.txt",
            mime="text/plain",
            text="Hello world",
        )
        assert d.source_type == "email"
        assert d.source_id == "msg_123"
        assert d.child_id == 3

    def test_child_has_search_profile_relationship(self) -> None:
        from storage.models import Child
        assert "search_profile_rel" in Child.__mapper__.relationships
        assert "gmail_messages" in Child.__mapper__.relationships
