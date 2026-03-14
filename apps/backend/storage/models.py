"""SQLAlchemy models for Parently."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    Boolean, Column, Date, DateTime, Float, ForeignKey, Index, Integer,
    String, Text, UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


def _utcnow() -> datetime:
    return datetime.utcnow()


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    provider: Mapped[str] = mapped_column(String(50), nullable=False, default="google")
    child_sort_mode: Mapped[str] = mapped_column(String(20), nullable=False, default="ALPHABETICAL")  # ALPHABETICAL, AGE_ASC, AGE_DESC
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow, nullable=False)

    integrations = relationship("UserIntegration", back_populates="user", cascade="all, delete-orphan")
    digests = relationship("Digest", back_populates="user", cascade="all, delete-orphan")
    children = relationship("Child", back_populates="user", cascade="all, delete-orphan")
    preferences = relationship("UserPreference", back_populates="user", uselist=False, cascade="all, delete-orphan")
    entitlement = relationship("UserEntitlement", back_populates="user", uselist=False, cascade="all, delete-orphan")
    stripe_customer = relationship("StripeCustomer", back_populates="user", uselist=False, cascade="all, delete-orphan")
    llm_usages = relationship("LLMUsage", back_populates="user", cascade="all, delete-orphan")
    digest_jobs = relationship("DigestJob", back_populates="user", cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")
    onboarding_complete: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class Child(Base):
    __tablename__ = "children"
    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_child_user_name"),
        Index("ix_children_user", "user_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)

    # Auto-populated / optional
    school_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    school_domain: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)  # e.g. "rrisd.org"
    grade: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    teacher_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    birthdate: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    photo_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Stable manual ordering (overrides sort mode)
    sort_order: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Lightweight search profile (auto-managed JSONB-like)
    # Example: {"gmail_query": "...", "sender_domains": ["rrisd.org"], "subject_keywords": [...]}
    search_profile_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    last_sync_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow, nullable=False)

    user = relationship("User", back_populates="children")
    search_profile_rel = relationship("ChildSearchProfile", back_populates="child", uselist=False, cascade="all, delete-orphan")
    gmail_messages = relationship("GmailMessageIndex", back_populates="child", cascade="all, delete-orphan")
    discovery_jobs = relationship("DiscoveryJob", back_populates="child", cascade="all, delete-orphan")
    school_sources = relationship("SchoolSource", back_populates="child", cascade="all, delete-orphan")

    def search_profile(self) -> Dict[str, Any]:
        """Return parsed search profile from JSON column."""
        if not self.search_profile_json:
            return {}
        return json.loads(self.search_profile_json)

    def set_search_profile(self, profile: Dict[str, Any]) -> None:
        """Serialize and store search profile."""
        self.search_profile_json = json.dumps(profile)


class ChildSearchProfile(Base):
    __tablename__ = "child_search_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    child_id: Mapped[int] = mapped_column(Integer, ForeignKey("children.id"), unique=True, nullable=False)
    gmail_query_base: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # manual override
    subject_keywords_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON array
    sender_allowlist_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON array
    sender_blocklist_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON array
    label_whitelist_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON array
    exclude_keywords_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON array
    last_sync_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    child = relationship("Child", back_populates="search_profile_rel")

    def subject_keywords(self) -> List[str]:
        return json.loads(self.subject_keywords_json) if self.subject_keywords_json else []

    def sender_allowlist(self) -> List[str]:
        return json.loads(self.sender_allowlist_json) if self.sender_allowlist_json else []

    def sender_blocklist(self) -> List[str]:
        return json.loads(self.sender_blocklist_json) if self.sender_blocklist_json else []

    def label_whitelist(self) -> List[str]:
        return json.loads(self.label_whitelist_json) if self.label_whitelist_json else []

    def exclude_keywords(self) -> List[str]:
        return json.loads(self.exclude_keywords_json) if self.exclude_keywords_json else []


class GmailMessageIndex(Base):
    __tablename__ = "gmail_message_index"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    child_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("children.id"), nullable=True)
    gmail_message_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    thread_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    internal_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    from_email: Mapped[Optional[str]] = mapped_column(String(320), nullable=True)
    subject: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    snippet: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    label_ids_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON array
    matched_rules_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON: which keyword/sender matched
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    child = relationship("Child", back_populates="gmail_messages")

    def label_ids(self) -> List[str]:
        return json.loads(self.label_ids_json) if self.label_ids_json else []

    def matched_rules(self) -> Dict[str, Any]:
        return json.loads(self.matched_rules_json) if self.matched_rules_json else {}


class UserPreference(Base):
    __tablename__ = "user_preferences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    digest_time: Mapped[str] = mapped_column(String(10), nullable=False, default="06:00")
    timezone: Mapped[str] = mapped_column(String(50), nullable=False, default="America/Chicago")
    email_notifications: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    push_notifications: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    urgent_alerts: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    lookback_days: Mapped[int] = mapped_column(Integer, nullable=False, default=7)

    user = relationship("User", back_populates="preferences")


class UserIntegration(Base):
    __tablename__ = "user_integrations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    platform: Mapped[str] = mapped_column(String(50), nullable=False)  # gmail, gdrive, skyward, classdojo, brightwheel
    credentials_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # encrypted JSON
    config_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # platform-specific settings
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="not_connected")  # connected, error, not_connected
    last_synced: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="integrations")

    def config(self) -> Dict[str, Any]:
        if not self.config_json:
            return {}
        return json.loads(self.config_json)


class Digest(Base):
    """One combined digest per user per day. Sections inside represent each kid."""
    __tablename__ = "digests"
    __table_args__ = (
        UniqueConstraint("user_id", "digest_date", name="uq_digest_user_date"),
        Index("ix_digests_user_date", "user_id", "digest_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    child_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("children.id"), nullable=True)
    digest_date: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)  # YYYY-MM-DD
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow, nullable=False)
    source: Mapped[str] = mapped_column(String(255), nullable=False)
    summary_md: Mapped[str] = mapped_column(Text, nullable=False)
    items_json: Mapped[str] = mapped_column(Text, nullable=False)
    raw_json: Mapped[str] = mapped_column(Text, nullable=False)
    source_counts_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    stats_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # optional stats for UI

    user = relationship("User", back_populates="digests")
    sections = relationship("DigestSection", back_populates="digest", cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="digest", cascade="all, delete-orphan")

    def items(self) -> List[Dict[str, Any]]:
        return json.loads(self.items_json)

    def raw(self) -> Dict[str, Any]:
        return json.loads(self.raw_json)

    def stats(self) -> Dict[str, Any]:
        return json.loads(self.stats_json) if self.stats_json else {}


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    child_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("children.id"), nullable=True)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False, default="pdf")  # email, pdf, drive-doc
    source_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # gmail_message_id, drive_id
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    mime: Mapped[str] = mapped_column(String(128), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    chunks_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    embeddings_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    embeddings_rel = relationship("Embedding", back_populates="document", cascade="all, delete-orphan")

    def chunks(self) -> List[str]:
        if not self.chunks_json:
            return []
        return json.loads(self.chunks_json)

    def embeddings(self) -> List[List[float]]:
        if not self.embeddings_json:
            return []
        return json.loads(self.embeddings_json)


class Embedding(Base):
    __tablename__ = "embeddings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    document_id: Mapped[int] = mapped_column(Integer, ForeignKey("documents.id"), nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    document = relationship("Document", back_populates="embeddings_rel")

    def get_embedding(self) -> List[float]:
        return json.loads(self.embedding_json)


class UserEntitlement(Base):
    __tablename__ = "user_entitlements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    plan: Mapped[str] = mapped_column(String(20), nullable=False, default="FREE")  # FREE, PREMIUM
    digests_remaining: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    premium_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    premium_started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    premium_ends_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    user = relationship("User", back_populates="entitlement")


class StripeCustomer(Base):
    __tablename__ = "stripe_customers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    stripe_customer_id: Mapped[str] = mapped_column(String(255), nullable=False)
    stripe_subscription_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="inactive")

    user = relationship("User", back_populates="stripe_customer")


class LLMUsage(Base):
    __tablename__ = "llm_usage"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    digest_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("digests.id"), nullable=True)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    prompt_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    estimated_cost_usd: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="llm_usages")


class Notification(Base):
    """Read/unread tracked here; digest remains in history forever."""
    __tablename__ = "notifications"
    __table_args__ = (
        Index("ix_notifications_user_read", "user_id", "is_read"),
        Index("ix_notifications_user_created", "user_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    digest_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("digests.id", ondelete="SET NULL"), nullable=True)
    type: Mapped[str] = mapped_column(String(50), nullable=False, default="DIGEST_READY")  # DIGEST_READY, URGENT_EVENT, CONNECTOR_ERROR, BILLING_EVENT, SYSTEM
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    body: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)

    user = relationship("User", back_populates="notifications")
    digest = relationship("Digest", back_populates="notifications")


class DigestSection(Base):
    """One section per child in a combined digest. sort_key determines UI ordering."""
    __tablename__ = "digest_sections"
    __table_args__ = (
        UniqueConstraint("digest_id", "child_id", name="uq_section_digest_child"),
        Index("ix_sections_digest", "digest_id"),
        Index("ix_sections_sort", "digest_id", "sort_key"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    digest_id: Mapped[int] = mapped_column(Integer, ForeignKey("digests.id", ondelete="CASCADE"), nullable=False)
    child_id: Mapped[int] = mapped_column(Integer, ForeignKey("children.id", ondelete="CASCADE"), nullable=False)
    sort_key: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    markdown: Mapped[str] = mapped_column(Text, nullable=False)
    stats_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)

    digest = relationship("Digest", back_populates="sections")
    child = relationship("Child")
    items = relationship("DigestItem", back_populates="section", cascade="all, delete-orphan")

    def stats(self) -> Dict[str, Any]:
        return json.loads(self.stats_json) if self.stats_json else {}


class DigestItem(Base):
    """Structured action items/events extracted per child section."""
    __tablename__ = "digest_items"
    __table_args__ = (
        Index("ix_items_section", "section_id"),
        Index("ix_items_due", "due_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    section_id: Mapped[int] = mapped_column(Integer, ForeignKey("digest_sections.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    summary: Mapped[Optional[str]] = mapped_column(String(800), nullable=True)
    priority: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)  # high|medium|low
    due_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    tags_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON
    origin_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON: message_id, url, etc.
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)

    section = relationship("DigestSection", back_populates="items")

    def tags(self) -> List[str]:
        return json.loads(self.tags_json) if self.tags_json else []

    def origin(self) -> Dict[str, Any]:
        return json.loads(self.origin_json) if self.origin_json else {}


class DigestJob(Base):
    __tablename__ = "digest_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="queued")  # queued, running, success, failed
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    digest_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("digests.id"), nullable=True)

    user = relationship("User", back_populates="digest_jobs")


class DiscoveryJob(Base):
    """Tracks school discovery requests (one per child per attempt)."""
    __tablename__ = "discovery_jobs"
    __table_args__ = (
        Index("ix_discovery_user", "user_id"),
        Index("ix_discovery_child", "child_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    child_id: Mapped[int] = mapped_column(Integer, ForeignKey("children.id", ondelete="CASCADE"), nullable=False)
    school_query_text: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="queued")  # queued, running, success, failed
    result_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON: candidates, scores, etc.
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    user = relationship("User")
    child = relationship("Child", back_populates="discovery_jobs")

    def result(self) -> Dict[str, Any]:
        return json.loads(self.result_json) if self.result_json else {}


class SchoolSource(Base):
    """Verified (or pending) school website/calendar source for a child."""
    __tablename__ = "school_sources"
    __table_args__ = (
        Index("ix_school_sources_child", "child_id"),
        Index("ix_school_sources_user", "user_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    child_id: Mapped[int] = mapped_column(Integer, ForeignKey("children.id", ondelete="CASCADE"), nullable=False)
    school_query: Mapped[str] = mapped_column(Text, nullable=False)  # original search text
    verified_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    homepage_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    district_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    calendar_page_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ics_urls_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON array
    rss_urls_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON array
    pdf_urls_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON array
    confidence_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="needs_confirmation")  # verified, needs_confirmation, failed
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow, nullable=False)
    last_ingested_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    user = relationship("User")
    child = relationship("Child", back_populates="school_sources")

    def ics_urls(self) -> List[str]:
        return json.loads(self.ics_urls_json) if self.ics_urls_json else []

    def rss_urls(self) -> List[str]:
        return json.loads(self.rss_urls_json) if self.rss_urls_json else []

    def pdf_urls(self) -> List[str]:
        return json.loads(self.pdf_urls_json) if self.pdf_urls_json else []
