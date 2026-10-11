"""搭子帖出入参。"""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class PostCreate(BaseModel):
    """发帖入参。"""

    destination: str = Field(min_length=1, max_length=120)
    depart_date: date
    need_count: int = Field(ge=2, description="需求人数，至少 2 人")
    note: str | None = Field(default=None, max_length=1000)


class PostOut(BaseModel):
    """帖子基础信息。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    owner_id: int
    owner_username: str | None = None
    destination: str
    depart_date: date
    need_count: int
    note: str | None = None
    status: str
    created_at: datetime


class ApplicantOut(BaseModel):
    """申请人（房间成员）摘要，仅帖主可见明细。"""

    member_id: int
    user_id: int
    username: str
    status: str


class PostDetailOut(PostOut):
    """帖子详情：附带房间与申请人列表（非帖主时 applicants 为空）。"""

    room_id: int | None = None
    applicants: list[ApplicantOut] = Field(default_factory=list)


class PostListOut(BaseModel):
    """分页列表。"""

    items: list[PostOut]
    total: int
