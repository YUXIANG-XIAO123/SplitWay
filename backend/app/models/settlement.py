"""结算与结算明细模型。"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Settlement(Base):
    """一次房间结算。

    ``room_id`` 唯一约束即幂等保证（B5）：同一房间只允许存在一条结算记录。
    """

    __tablename__ = "settlements"

    id: Mapped[int] = mapped_column(primary_key=True)
    room_id: Mapped[int] = mapped_column(
        ForeignKey("rooms.id"), nullable=False, unique=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    items: Mapped[list["SettlementItem"]] = relationship(
        back_populates="settlement", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Settlement id={self.id} room_id={self.room_id}>"


class SettlementItem(Base):
    """结算结果中某个成员的一行。"""

    __tablename__ = "settlement_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    settlement_id: Mapped[int] = mapped_column(
        ForeignKey("settlements.id"), nullable=False, index=True
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )
    paid_cents: Mapped[int] = mapped_column(BigInteger, nullable=False)
    share_cents: Mapped[int] = mapped_column(BigInteger, nullable=False)
    net_cents: Mapped[int] = mapped_column(BigInteger, nullable=False)

    settlement: Mapped[Settlement] = relationship(back_populates="items")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<SettlementItem settlement_id={self.settlement_id} user_id={self.user_id}>"
