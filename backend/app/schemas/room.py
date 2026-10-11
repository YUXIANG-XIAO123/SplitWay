"""房间与成员出入参。"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class RoomCreate(BaseModel):
    """创建房间入参（仅帖子所有者可调用）。"""

    post_id: int = Field(gt=0)


class RoomOut(BaseModel):
    """房间基础信息。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    post_id: int
    owner_id: int
    status: str
    member_limit: int
    created_at: datetime


class MemberOut(BaseModel):
    """房间成员信息。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    room_id: int
    user_id: int
    username: str | None = None
    status: str
    role: str
    created_at: datetime


class JoinRequestOut(MemberOut):
    """申请结果（pending 成员记录）。"""


class RoomDetailOut(RoomOut):
    """房间详情：附带成员列表。"""

    members: list[MemberOut] = Field(default_factory=list)
