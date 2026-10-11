"""bills 与 bill_shares 表。

Revision ID: 0004_bills
Revises: 0003_rooms
Create Date: 2026-09-28
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_bills"
down_revision: str | None = "0003_rooms"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "bills",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("room_id", sa.Integer(), sa.ForeignKey("rooms.id"), nullable=False),
        sa.Column("payer_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("amount_cents", sa.BigInteger(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint("amount_cents > 0", name="ck_bills_amount_positive"),
    )
    op.create_index("ix_bills_room_id", "bills", ["room_id"])
    op.create_index("ix_bills_payer_id", "bills", ["payer_id"])

    op.create_table(
        "bill_shares",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("bill_id", sa.Integer(), sa.ForeignKey("bills.id"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("amount_cents", sa.BigInteger(), nullable=False),
    )
    op.create_index("ix_bill_shares_bill_id", "bill_shares", ["bill_id"])
    op.create_index("ix_bill_shares_user_id", "bill_shares", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_bill_shares_user_id", table_name="bill_shares")
    op.drop_index("ix_bill_shares_bill_id", table_name="bill_shares")
    op.drop_table("bill_shares")
    op.drop_index("ix_bills_payer_id", table_name="bills")
    op.drop_index("ix_bills_room_id", table_name="bills")
    op.drop_table("bills")
