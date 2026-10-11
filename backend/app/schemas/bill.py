"""账单出入参。"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class BillCreate(BaseModel):
    """新增账单入参。

    - ``payer_id`` 为**用户 ID**，省略时默认操作者本人；指定时必须为房间 joined 成员。
    - ``participant_member_ids`` 为**房间成员 ID**（``room_members.id``）列表，非空，
      且必须全部为房间 joined 成员。
    - 金额单位为**整数分**，必须 > 0。
    """

    payer_id: int | None = Field(default=None, gt=0)
    amount_cents: int = Field(gt=0, description="金额，单位：分")
    note: str | None = Field(default=None, max_length=1000)
    participant_member_ids: list[int] = Field(min_length=1)


class BillShareOut(BaseModel):
    """单条分摊明细。"""

    model_config = ConfigDict(from_attributes=True)

    user_id: int
    amount_cents: int


class BillOut(BaseModel):
    """账单（含分摊明细）。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    room_id: int
    payer_id: int
    amount_cents: int
    note: str | None = None
    created_at: datetime
    shares: list[BillShareOut] = Field(default_factory=list)
