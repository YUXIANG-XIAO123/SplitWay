"""账单与账单分摊模型。

金额全程为整数分（BIGINT），不出现浮点。
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Bill(Base):
    """房间内的一条账单。"""

    __tablename__ = "bills"

    id: Mapped[int] = mapped_column(primary_key=True)
    room_id: Mapped[int] = mapped_column(
        ForeignKey("rooms.id"), nullable=False, index=True
    )
    payer_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )
    amount_cents: Mapped[int] = mapped_column(BigInteger, nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    shares: Mapped[list["BillShare"]] = relationship(
        back_populates="bill", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Bill id={self.id} room_id={self.room_id} amount_cents={self.amount_cents}>"


class BillShare(Base):
    """账单分摊明细（每人一行）。"""

    __tablename__ = "bill_shares"

    id: Mapped[int] = mapped_column(primary_key=True)
    bill_id: Mapped[int] = mapped_column(
        ForeignKey("bills.id"), nullable=False, index=True
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )
    amount_cents: Mapped[int] = mapped_column(BigInteger, nullable=False)

    bill: Mapped[Bill] = relationship(back_populates="shares")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<BillShare bill_id={self.bill_id} user_id={self.user_id}>"
