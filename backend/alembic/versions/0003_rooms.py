"""rooms 与 room_members 表，含部分唯一索引。

Revision ID: 0003_rooms
Revises: 0002_posts
Create Date: 2026-09-28
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_rooms"
down_revision: str | None = "0002_posts"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "rooms",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("post_id", sa.Integer(), sa.ForeignKey("partner_posts.id"), nullable=False),
        sa.Column("owner_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column(
            "status", sa.String(length=16), nullable=False, server_default=sa.text("'open'")
        ),
        sa.Column("member_limit", sa.Integer(), nullable=False, server_default=sa.text("20")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_rooms_post_id", "rooms", ["post_id"])
    op.create_index("ix_rooms_owner_id", "rooms", ["owner_id"])

    op.create_table(
        "room_members",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("room_id", sa.Integer(), sa.ForeignKey("rooms.id"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column(
            "status", sa.String(length=16), nullable=False, server_default=sa.text("'pending'")
        ),
        sa.Column(
            "role", sa.String(length=16), nullable=False, server_default=sa.text("'member'")
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_room_members_room_id", "room_members", ["room_id"])
    op.create_index("ix_room_members_user_id", "room_members", ["user_id"])

    # 关键约束：同一房间内，同一用户的有效成员记录（pending/joined）只能有一条。
    op.create_index(
        "uq_room_member_active",
        "room_members",
        ["room_id", "user_id"],
        unique=True,
        postgresql_where=sa.text("status IN ('pending', 'joined')"),
    )


def downgrade() -> None:
    op.drop_index("uq_room_member_active", table_name="room_members")
    op.drop_index("ix_room_members_user_id", table_name="room_members")
    op.drop_index("ix_room_members_room_id", table_name="room_members")
    op.drop_table("room_members")
    op.drop_index("ix_rooms_owner_id", table_name="rooms")
    op.drop_index("ix_rooms_post_id", table_name="rooms")
    op.drop_table("rooms")
