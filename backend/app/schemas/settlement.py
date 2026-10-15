"""结算出入参。"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class SettlementItemOut(BaseModel):
    """结算结果中的一行。

    **只以 ``user_id`` 标识主体。** 结算是账务快照，财务主体是"人"，不是"房间成员记录"。

    历史上这里还有一个 ``member_id``，但它是**读取时按当前成员记录反查**的
    （取该用户在该房间 id 最大的那条），并非结算时固化下来的值 —— 会随成员记录的增删而漂移，
    属于会误导的展示字段。既然它不参与任何账务计算，直接移除；需要成员信息请查房间成员接口。
    """

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
