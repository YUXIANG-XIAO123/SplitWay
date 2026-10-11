"""partner_posts 表。

Revision ID: 0002_posts
Revises: 0001_users
Create Date: 2026-09-28
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_posts"
down_revision: str | None = "0001_users"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "partner_posts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("owner_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("destination", sa.String(length=120), nullable=False),
        sa.Column("depart_date", sa.Date(), nullable=False),
        sa.Column("need_count", sa.Integer(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column(
            "status", sa.String(length=16), nullable=False, server_default=sa.text("'open'")
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_partner_posts_owner_id", "partner_posts", ["owner_id"])


def downgrade() -> None:
    op.drop_index("ix_partner_posts_owner_id", table_name="partner_posts")
    op.drop_table("partner_posts")
