"""房间与房间成员模型。"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

# 房间状态：open 进行中 / settled 已结算（只读）。
ROOM_STATUS_OPEN = "open"
ROOM_STATUS_SETTLED = "settled"

# 成员状态（四态）。
MEMBER_STATUS_PENDING = "pending"
MEMBER_STATUS_JOINED = "joined"
MEMBER_STATUS_REJECTED = "rejected"
MEMBER_STATUS_LEFT = "left"

# 成员角色。
MEMBER_ROLE_OWNER = "owner"
MEMBER_ROLE_MEMBER = "member"

# 有效成员 = pending 或 joined；rejected / left 是历史记录，可再次申请。
ACTIVE_MEMBER_STATUSES = (MEMBER_STATUS_PENDING, MEMBER_STATUS_JOINED)


class Room(Base):
    """基于搭子帖创建的房间。"""

    __tablename__ = "rooms"

    id: Mapped[int] = mapped_column(primary_key=True)
    post_id: Mapped[int] = mapped_column(
        ForeignKey("partner_posts.id"), nullable=False, index=True
    )
    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, server_default=ROOM_STATUS_OPEN
    )
    member_limit: Mapped[int] = mapped_column(Integer, nullable=False, server_default="20")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    members: Mapped[list["RoomMember"]] = relationship(
        back_populates="room", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Room id={self.id} status={self.status}>"


class RoomMember(Base):
    """房间成员记录，承载四态状态机。"""

    __tablename__ = "room_members"

    id: Mapped[int] = mapped_column(primary_key=True)
    room_id: Mapped[int] = mapped_column(
        ForeignKey("rooms.id"), nullable=False, index=True
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, server_default=MEMBER_STATUS_PENDING
    )
    role: Mapped[str] = mapped_column(
        String(16), nullable=False, server_default=MEMBER_ROLE_MEMBER
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    room: Mapped[Room] = relationship(back_populates="members")

    __table_args__ = (
        # 关键约束：同一房间内，同一用户的"有效成员记录"只能有一条。
        # 有效 = pending 或 joined（PostgreSQL 部分唯一索引），在 DB 层兜底重复申请/重复加入。
        Index(
            "uq_room_member_active",
            "room_id",
            "user_id",
            unique=True,
            postgresql_where=text("status IN ('pending', 'joined')"),
        ),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<RoomMember id={self.id} room_id={self.room_id} "
            f"user_id={self.user_id} status={self.status}>"
        )
