"""schema_refactor_chunks_vectors_setup

Revision ID: b7c8d9e0f1a2
Revises: a1b2c3d4e5f6
Create Date: 2026-03-15 11:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b7c8d9e0f1a2"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # documents: explicit document storage fields
    op.add_column("documents", sa.Column("title", sa.String(length=255), nullable=True))
    op.add_column("documents", sa.Column("content", sa.Text(), nullable=True))
    op.add_column("documents", sa.Column("metadata_json", sa.Text(), nullable=True))
    op.execute("UPDATE documents SET title = COALESCE(filename, 'Document') WHERE title IS NULL")
    op.execute("UPDATE documents SET content = COALESCE(text, '') WHERE content IS NULL")
    if dialect == "postgresql":
        op.alter_column("documents", "title", nullable=False)
        op.alter_column("documents", "content", nullable=False)

    # document_chunks: normalized chunk store
    op.create_table(
        "document_chunks",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("chunk_text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("document_id", "chunk_index", name="uq_document_chunk_index"),
    )
    op.create_index("ix_document_chunks_document", "document_chunks", ["document_id"], unique=False)

    # embeddings: vector-based + chunk reference
    op.add_column("embeddings", sa.Column("document_chunk_id", sa.Integer(), nullable=True))
    if dialect != "sqlite":
        op.create_foreign_key(
            "fk_embeddings_document_chunk_id",
            "embeddings",
            "document_chunks",
            ["document_chunk_id"],
            ["id"],
            ondelete="CASCADE",
        )
    if dialect == "postgresql":
        op.execute("ALTER TABLE embeddings ADD COLUMN embedding vector(1536)")
    else:
        op.add_column("embeddings", sa.Column("embedding", sa.Text(), nullable=True))

    # Backfill chunk rows from existing embeddings
    op.execute(
        """
        INSERT INTO document_chunks (document_id, chunk_index, chunk_text, created_at)
        SELECT e.document_id, e.chunk_index, e.chunk_text, COALESCE(e.created_at, CURRENT_TIMESTAMP)
        FROM embeddings e
        LEFT JOIN document_chunks dc
          ON dc.document_id = e.document_id AND dc.chunk_index = e.chunk_index
        WHERE dc.id IS NULL
        """
    )
    op.execute(
        """
        UPDATE embeddings
        SET document_chunk_id = (
            SELECT dc.id
            FROM document_chunks dc
            WHERE dc.document_id = embeddings.document_id
              AND dc.chunk_index = embeddings.chunk_index
            LIMIT 1
        )
        WHERE document_chunk_id IS NULL
        """
    )
    if dialect == "postgresql":
        op.execute(
            """
            UPDATE embeddings
            SET embedding = CAST(embedding_json AS vector)
            WHERE embedding_json IS NOT NULL AND embedding IS NULL
            """
        )
        op.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_embeddings_vector
            ON embeddings
            USING ivfflat (embedding vector_cosine_ops)
            WITH (lists = 100)
            """
        )
    else:
        op.execute(
            """
            UPDATE embeddings
            SET embedding = embedding_json
            WHERE embedding_json IS NOT NULL AND embedding IS NULL
            """
        )

    # school_sources: explicit source model fields + normalized state values
    op.add_column("school_sources", sa.Column("source_type", sa.String(length=20), nullable=True))
    op.add_column("school_sources", sa.Column("source_url", sa.Text(), nullable=True))
    op.execute("UPDATE school_sources SET source_type = 'website' WHERE source_type IS NULL")
    op.execute("UPDATE school_sources SET source_url = COALESCE(homepage_url, calendar_page_url) WHERE source_url IS NULL")
    op.execute("UPDATE school_sources SET status = 'linked' WHERE status = 'verified'")
    if dialect == "postgresql":
        op.alter_column("school_sources", "source_type", nullable=False)

    # user_integrations: provider/scopes split from app-login auth
    op.add_column("user_integrations", sa.Column("provider", sa.String(length=50), nullable=True))
    op.add_column("user_integrations", sa.Column("granted_scopes", sa.Text(), nullable=True))
    op.execute(
        """
        UPDATE user_integrations
        SET provider = CASE
            WHEN platform = 'gdrive' THEN 'google_drive'
            ELSE platform
        END
        WHERE provider IS NULL
        """
    )
    op.execute("UPDATE user_integrations SET status = 'scope_missing' WHERE status = 'pending_confirmation'")
    if dialect == "postgresql":
        op.alter_column("user_integrations", "provider", nullable=False)


def downgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "postgresql":
        op.execute("DROP INDEX IF EXISTS idx_embeddings_vector")
        op.execute("ALTER TABLE embeddings DROP COLUMN IF EXISTS embedding")
    else:
        op.drop_column("embeddings", "embedding")
    if dialect != "sqlite":
        op.drop_constraint("fk_embeddings_document_chunk_id", "embeddings", type_="foreignkey")
    op.drop_column("embeddings", "document_chunk_id")

    op.drop_index("ix_document_chunks_document", table_name="document_chunks")
    op.drop_table("document_chunks")

    op.drop_column("documents", "metadata_json")
    op.drop_column("documents", "content")
    op.drop_column("documents", "title")

    op.execute("UPDATE school_sources SET status = 'verified' WHERE status = 'linked'")
    op.drop_column("school_sources", "source_url")
    op.drop_column("school_sources", "source_type")

    op.drop_column("user_integrations", "granted_scopes")
    op.drop_column("user_integrations", "provider")
