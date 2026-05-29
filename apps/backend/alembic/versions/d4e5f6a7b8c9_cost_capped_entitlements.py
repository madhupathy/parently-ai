"""cost-capped entitlements

Adds lifetime_cost_usd_cents + cost_cap_usd_cents columns to user_entitlements
so we can gate the free tier by accumulated LLM spend instead of digest count.

Revision ID: d4e5f6a7b8c9
Revises: c3f4b5a6d7e8
Create Date: 2026-05-29 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, None] = "c3f4b5a6d7e8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("user_entitlements") as batch_op:
        batch_op.add_column(
            sa.Column(
                "lifetime_cost_usd_cents",
                sa.Integer(),
                nullable=False,
                server_default="0",
            )
        )
        batch_op.add_column(
            sa.Column(
                "cost_cap_usd_cents",
                sa.Integer(),
                nullable=False,
                server_default="500",
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("user_entitlements") as batch_op:
        batch_op.drop_column("cost_cap_usd_cents")
        batch_op.drop_column("lifetime_cost_usd_cents")
