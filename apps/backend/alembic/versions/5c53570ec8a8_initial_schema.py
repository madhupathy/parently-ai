"""initial_schema

Revision ID: 5c53570ec8a8
Revises: 
Create Date: 2026-02-23 20:45:05.772634

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5c53570ec8a8'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("avatar_url", sa.Text(), nullable=True),
        sa.Column("provider", sa.String(length=50), nullable=False, server_default="google"),
        sa.Column("child_sort_mode", sa.String(length=20), nullable=False, server_default="ALPHABETICAL"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("onboarding_complete", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )

    op.create_table(
        "children",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("school_name", sa.String(length=200), nullable=True),
        sa.Column("school_domain", sa.String(length=120), nullable=True),
        sa.Column("grade", sa.String(length=50), nullable=True),
        sa.Column("teacher_name", sa.String(length=255), nullable=True),
        sa.Column("birthdate", sa.String(length=20), nullable=True),
        sa.Column("photo_url", sa.Text(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=True),
        sa.Column("search_profile_json", sa.Text(), nullable=True),
        sa.Column("last_sync_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "name", name="uq_child_user_name"),
    )
    op.create_index("ix_children_user", "children", ["user_id"], unique=False)

    op.create_table(
        "child_search_profiles",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("child_id", sa.Integer(), nullable=False),
        sa.Column("gmail_query_base", sa.Text(), nullable=True),
        sa.Column("subject_keywords_json", sa.Text(), nullable=True),
        sa.Column("sender_allowlist_json", sa.Text(), nullable=True),
        sa.Column("sender_blocklist_json", sa.Text(), nullable=True),
        sa.Column("label_whitelist_json", sa.Text(), nullable=True),
        sa.Column("exclude_keywords_json", sa.Text(), nullable=True),
        sa.Column("last_sync_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["child_id"], ["children.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("child_id"),
    )

    op.create_table(
        "gmail_message_index",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("child_id", sa.Integer(), nullable=True),
        sa.Column("gmail_message_id", sa.String(length=255), nullable=False),
        sa.Column("thread_id", sa.String(length=255), nullable=True),
        sa.Column("internal_date", sa.DateTime(), nullable=True),
        sa.Column("from_email", sa.String(length=320), nullable=True),
        sa.Column("subject", sa.Text(), nullable=True),
        sa.Column("snippet", sa.Text(), nullable=True),
        sa.Column("label_ids_json", sa.Text(), nullable=True),
        sa.Column("matched_rules_json", sa.Text(), nullable=True),
        sa.Column("fetched_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["child_id"], ["children.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("gmail_message_id"),
    )

    op.create_table(
        "user_preferences",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("digest_time", sa.String(length=10), nullable=False, server_default="06:00"),
        sa.Column("timezone", sa.String(length=50), nullable=False, server_default="America/Chicago"),
        sa.Column("email_notifications", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("push_notifications", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("urgent_alerts", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("lookback_days", sa.Integer(), nullable=False, server_default="7"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )

    op.create_table(
        "user_integrations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("platform", sa.String(length=50), nullable=False),
        sa.Column("credentials_json", sa.Text(), nullable=True),
        sa.Column("config_json", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="not_connected"),
        sa.Column("last_synced", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "digests",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("child_id", sa.Integer(), nullable=True),
        sa.Column("digest_date", sa.String(length=10), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("source", sa.String(length=255), nullable=False),
        sa.Column("summary_md", sa.Text(), nullable=False),
        sa.Column("items_json", sa.Text(), nullable=False),
        sa.Column("raw_json", sa.Text(), nullable=False),
        sa.Column("source_counts_json", sa.Text(), nullable=True),
        sa.Column("stats_json", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["child_id"], ["children.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "digest_date", name="uq_digest_user_date"),
    )
    op.create_index("ix_digests_user_date", "digests", ["user_id", "digest_date"], unique=False)

    op.create_table(
        "documents",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("child_id", sa.Integer(), nullable=True),
        sa.Column("source_type", sa.String(length=50), nullable=False, server_default="pdf"),
        sa.Column("source_id", sa.String(length=255), nullable=True),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("mime", sa.String(length=128), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("chunks_json", sa.Text(), nullable=True),
        sa.Column("embeddings_json", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["child_id"], ["children.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("digest_id", sa.Integer(), nullable=True),
        sa.Column("type", sa.String(length=50), nullable=False, server_default="DIGEST_READY"),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("read_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["digest_id"], ["digests.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_notifications_user_read", "notifications", ["user_id", "is_read"], unique=False)
    op.create_index("ix_notifications_user_created", "notifications", ["user_id", "created_at"], unique=False)

    op.create_table(
        "digest_sections",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("digest_id", sa.Integer(), nullable=False),
        sa.Column("child_id", sa.Integer(), nullable=False),
        sa.Column("sort_key", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("markdown", sa.Text(), nullable=False),
        sa.Column("stats_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["child_id"], ["children.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["digest_id"], ["digests.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("digest_id", "child_id", name="uq_section_digest_child"),
    )
    op.create_index("ix_sections_digest", "digest_sections", ["digest_id"], unique=False)
    op.create_index("ix_sections_sort", "digest_sections", ["digest_id", "sort_key"], unique=False)

    op.create_table(
        "digest_items",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("section_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("summary", sa.String(length=800), nullable=True),
        sa.Column("priority", sa.String(length=16), nullable=True),
        sa.Column("due_at", sa.DateTime(), nullable=True),
        sa.Column("tags_json", sa.Text(), nullable=True),
        sa.Column("origin_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["section_id"], ["digest_sections.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_items_section", "digest_items", ["section_id"], unique=False)
    op.create_index("ix_items_due", "digest_items", ["due_at"], unique=False)

    op.create_table(
        "discovery_jobs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("child_id", sa.Integer(), nullable=False),
        sa.Column("school_query_text", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="queued"),
        sa.Column("result_json", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["child_id"], ["children.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_discovery_user", "discovery_jobs", ["user_id"], unique=False)
    op.create_index("ix_discovery_child", "discovery_jobs", ["child_id"], unique=False)

    op.create_table(
        "school_sources",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("child_id", sa.Integer(), nullable=False),
        sa.Column("school_query", sa.Text(), nullable=False),
        sa.Column("verified_name", sa.String(length=255), nullable=True),
        sa.Column("homepage_url", sa.Text(), nullable=True),
        sa.Column("district_url", sa.Text(), nullable=True),
        sa.Column("calendar_page_url", sa.Text(), nullable=True),
        sa.Column("ics_urls_json", sa.Text(), nullable=True),
        sa.Column("rss_urls_json", sa.Text(), nullable=True),
        sa.Column("pdf_urls_json", sa.Text(), nullable=True),
        sa.Column("confidence_score", sa.Float(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="needs_confirmation"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("last_ingested_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["child_id"], ["children.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_school_sources_child", "school_sources", ["child_id"], unique=False)
    op.create_index("ix_school_sources_user", "school_sources", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_school_sources_user", table_name="school_sources")
    op.drop_index("ix_school_sources_child", table_name="school_sources")
    op.drop_table("school_sources")

    op.drop_index("ix_discovery_child", table_name="discovery_jobs")
    op.drop_index("ix_discovery_user", table_name="discovery_jobs")
    op.drop_table("discovery_jobs")

    op.drop_index("ix_items_due", table_name="digest_items")
    op.drop_index("ix_items_section", table_name="digest_items")
    op.drop_table("digest_items")

    op.drop_index("ix_sections_sort", table_name="digest_sections")
    op.drop_index("ix_sections_digest", table_name="digest_sections")
    op.drop_table("digest_sections")

    op.drop_index("ix_notifications_user_created", table_name="notifications")
    op.drop_index("ix_notifications_user_read", table_name="notifications")
    op.drop_table("notifications")

    op.drop_table("documents")

    op.drop_index("ix_digests_user_date", table_name="digests")
    op.drop_table("digests")

    op.drop_table("user_integrations")
    op.drop_table("user_preferences")
    op.drop_table("gmail_message_index")
    op.drop_table("child_search_profiles")

    op.drop_index("ix_children_user", table_name="children")
    op.drop_table("children")

    op.drop_table("users")
