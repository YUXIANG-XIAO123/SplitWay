"""settlements 与 settlement_items 表。

Revision ID: 0005_settlements
Revises: 0004_bills
Create Date: 2026-09-28
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005_settlements"
down_revision: str | None = "0004_bills"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "settlements",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "room_id", sa.Integer(), sa.ForeignKey("rooms.id"), nullable=False, unique=True
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_settlements_room_id", "settlements", ["room_id"], unique=True)

    op.create_table(
        "settlement_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "settlement_id", sa.Integer(), sa.ForeignKey("settlements.id"), nullable=False
        ),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("paid_cents", sa.BigInteger(), nullable=False),
        sa.Column("share_cents", sa.BigInteger(), nullable=False),
        sa.Column("net_cents", sa.BigInteger(), nullable=False),
    )
    op.create_index("ix_settlement_items_settlement_id", "settlement_items", ["settlement_id"])
    op.create_index("ix_settlement_items_user_id", "settlement_items", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_settlement_items_user_id", table_name="settlement_items")
    op.drop_index("ix_settlement_items_settlement_id", table_name="settlement_items")
    op.drop_table("settlement_items")
    op.drop_index("ix_settlements_room_id", table_name="settlements")
    op.drop_table("settlements")
