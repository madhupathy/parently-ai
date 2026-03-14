"""Tests for children models and preferences models."""

from __future__ import annotations

from pydantic import BaseModel
from typing import Optional


# Re-declare the Pydantic models here to avoid importing through routers/__init__
# which pulls in billing.py → stripe (not installed in test env).
class ChildCreate(BaseModel):
    name: str
    grade: Optional[str] = None
    school_name: Optional[str] = None
    teacher_name: Optional[str] = None
    birthdate: Optional[str] = None


class ChildUpdate(BaseModel):
    name: Optional[str] = None
    grade: Optional[str] = None
    school_name: Optional[str] = None
    teacher_name: Optional[str] = None
    birthdate: Optional[str] = None


class TestChildModels:
    """Tests for Pydantic request models."""

    def test_child_create_required_name(self) -> None:
        c = ChildCreate(name="Emma")
        assert c.name == "Emma"
        assert c.grade is None
        assert c.school_name is None

    def test_child_create_all_fields(self) -> None:
        c = ChildCreate(
            name="Vedant",
            grade="3rd Grade",
            school_name="Lincoln Elementary",
            teacher_name="Ms. Garcia",
            birthdate="2018-05-15",
        )
        assert c.name == "Vedant"
        assert c.grade == "3rd Grade"
        assert c.school_name == "Lincoln Elementary"
        assert c.teacher_name == "Ms. Garcia"
        assert c.birthdate == "2018-05-15"

    def test_child_update_partial(self) -> None:
        u = ChildUpdate(grade="4th Grade")
        assert u.name is None
        assert u.grade == "4th Grade"

    def test_child_update_empty(self) -> None:
        u = ChildUpdate()
        assert u.name is None
        assert u.grade is None
        assert u.school_name is None


class TestChildSQLModel:
    """Tests for the Child SQLAlchemy model."""

    def test_child_fields(self) -> None:
        from storage.models import Child
        child = Child(
            user_id=1,
            name="Emma",
            grade="2nd Grade",
            school_name="Oak School",
            teacher_name="Mr. Lee",
        )
        assert child.name == "Emma"
        assert child.grade == "2nd Grade"
        assert child.school_name == "Oak School"
        assert child.teacher_name == "Mr. Lee"
        assert child.user_id == 1


class TestUserPreferenceSQLModel:
    """Tests for UserPreference SQLAlchemy model."""

    def test_preference_explicit_values(self) -> None:
        from storage.models import UserPreference
        pref = UserPreference(
            user_id=2,
            digest_time="19:00",
            timezone="America/New_York",
            email_notifications=False,
            push_notifications=True,
            urgent_alerts=False,
            lookback_days=3,
        )
        assert pref.digest_time == "19:00"
        assert pref.timezone == "America/New_York"
        assert pref.email_notifications is False
        assert pref.push_notifications is True
        assert pref.lookback_days == 3

    def test_preference_table_name(self) -> None:
        from storage.models import UserPreference
        assert UserPreference.__tablename__ == "user_preferences"


class TestUserOnboarding:
    """Tests for User onboarding_complete field."""

    def test_user_onboarding_explicit_false(self) -> None:
        from storage.models import User
        user = User(email="test@example.com", provider="google", onboarding_complete=False)
        assert user.onboarding_complete is False

    def test_user_onboarding_set_true(self) -> None:
        from storage.models import User
        user = User(email="test@example.com", provider="google", onboarding_complete=True)
        assert user.onboarding_complete is True

    def test_user_has_children_relationship(self) -> None:
        from storage.models import User
        # Verify the relationship attribute exists on the mapper
        assert "children" in User.__mapper__.relationships
        assert "preferences" in User.__mapper__.relationships


class TestDigestNewFields:
    """Tests for new Digest model fields."""

    def test_digest_child_id_nullable(self) -> None:
        from storage.models import Digest
        d = Digest(
            user_id=1,
            source="test",
            summary_md="# Test",
            items_json="[]",
            raw_json="{}",
        )
        assert d.child_id is None
        assert d.digest_date is None
        assert d.source_counts_json is None

    def test_digest_with_child(self) -> None:
        from storage.models import Digest
        d = Digest(
            user_id=1,
            child_id=5,
            digest_date="2026-02-26",
            source="cron",
            summary_md="# Digest",
            items_json="[]",
            raw_json="{}",
            source_counts_json='{"gmail": 3}',
        )
        assert d.child_id == 5
        assert d.digest_date == "2026-02-26"
        assert d.source_counts_json == '{"gmail": 3}'
