"""结算出入参。"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class SettlementItemOut(BaseModel):
    """结算结果中某个成员的一行。"""

    member_id: int
    user_id: int
    username: str
    paid_cents: int
    share_cents: int
    net_cents: int


class SettlementCheck(BaseModel):
    """不变式字段：供验收脚本直接读取（B3）。"""

    sum_share_equals_total: bool


class SettlementOut(BaseModel):
    """结算结果。"""

    room_id: int
    settled_at: datetime
    items: list[SettlementItemOut]
    total_cents: int
    check: SettlementCheck
