"""expand_user_integration_columns

Revision ID: c3f4b5a6d7e8
Revises: b7c8d9e0f1a2
Create Date: 2026-03-15 16:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c3f4b5a6d7e8"
down_revision: Union[str, None] = "b7c8d9e0f1a2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("user_integrations") as batch_op:
        batch_op.alter_column(
            "platform",
            existing_type=sa.String(length=50),
            type_=sa.String(length=64),
            existing_nullable=False,
        )
        batch_op.alter_column(
            "provider",
            existing_type=sa.String(length=50),
            type_=sa.String(length=64),
            existing_nullable=False,
        )
        batch_op.alter_column(
            "status",
            existing_type=sa.String(length=20),
            type_=sa.String(length=64),
            existing_nullable=False,
            existing_server_default=sa.text("'not_connected'"),
        )


def downgrade() -> None:
    # Normalize long values before shrinking columns.
    op.execute(
        """
        UPDATE user_integrations
        SET status = 'scope_missing'
        WHERE status = 'reauthorization_required'
        """
    )
    with op.batch_alter_table("user_integrations") as batch_op:
        batch_op.alter_column(
            "status",
            existing_type=sa.String(length=64),
            type_=sa.String(length=20),
            existing_nullable=False,
            existing_server_default=sa.text("'not_connected'"),
        )
        batch_op.alter_column(
            "provider",
            existing_type=sa.String(length=64),
            type_=sa.String(length=50),
            existing_nullable=False,
        )
        batch_op.alter_column(
            "platform",
            existing_type=sa.String(length=64),
            type_=sa.String(length=50),
            existing_nullable=False,
        )
