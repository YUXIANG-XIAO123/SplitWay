"""搭子帖模型。"""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base

# 帖子状态取值：open 招募中 / closed 已关闭。
POST_STATUS_OPEN = "open"
POST_STATUS_CLOSED = "closed"


class PartnerPost(Base):
    """找搭子帖子。"""

    __tablename__ = "partner_posts"

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )
    destination: Mapped[str] = mapped_column(String(120), nullable=False)
    depart_date: Mapped[date] = mapped_column(Date, nullable=False)
    need_count: Mapped[int] = mapped_column(Integer, nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, server_default=POST_STATUS_OPEN
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<PartnerPost id={self.id} destination={self.destination!r}>"
