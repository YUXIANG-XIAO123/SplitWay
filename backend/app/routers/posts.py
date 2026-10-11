"""搭子帖路由：发帖 / 列表分页 / 详情 / 删除（仅帖主）。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.errors import conflict, forbidden, not_found
from app.models.post import POST_STATUS_OPEN, PartnerPost
from app.models.room import MEMBER_STATUS_PENDING, Room, RoomMember
from app.models.user import User
from app.schemas.post import ApplicantOut, PostCreate, PostDetailOut, PostListOut, PostOut

router = APIRouter()


def _to_post_out(post: PartnerPost, owner_username: str | None) -> PostOut:
    """把 ORM 帖子对象转为出参。"""
    return PostOut(
        id=post.id,
        owner_id=post.owner_id,
        owner_username=owner_username,
        destination=post.destination,
        depart_date=post.depart_date,
        need_count=post.need_count,
        note=post.note,
        status=post.status,
        created_at=post.created_at,
    )


@router.post("", status_code=201, response_model=PostOut)
def create_post(
    payload: PostCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PostOut:
    """发布搭子帖。"""
    post = PartnerPost(
        owner_id=current_user.id,
        destination=payload.destination,
        depart_date=payload.depart_date,
        need_count=payload.need_count,
        note=payload.note,
        status=POST_STATUS_OPEN,
    )
    db.add(post)
    db.commit()
    db.refresh(post)
    return _to_post_out(post, current_user.username)


@router.get("", response_model=PostListOut)
def list_posts(
    status: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> PostListOut:
    """分页浏览搭子帖。"""
    conditions = []
    if status is not None:
        conditions.append(PartnerPost.status == status)

    total_stmt = select(func.count()).select_from(PartnerPost)
    list_stmt = select(PartnerPost, User.username).join(User, User.id == PartnerPost.owner_id)
    for condition in conditions:
        total_stmt = total_stmt.where(condition)
        list_stmt = list_stmt.where(condition)

    total = int(db.execute(total_stmt).scalar_one())
    list_stmt = list_stmt.order_by(PartnerPost.id.desc()).offset((page - 1) * size).limit(size)
    rows = db.execute(list_stmt).all()

    items = [_to_post_out(post, owner_username) for post, owner_username in rows]
    return PostListOut(items=items, total=total)


@router.get("/{post_id}", response_model=PostDetailOut)
def get_post(
    post_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PostDetailOut:
    """帖子详情；仅帖主可见申请人明细。"""
    post = db.get(PartnerPost, post_id)
    if post is None:
        raise not_found("帖子不存在。")

    owner_username = db.execute(
        select(User.username).where(User.id == post.owner_id)
    ).scalar_one_or_none()

    room = db.execute(
        select(Room).where(Room.post_id == post.id).order_by(Room.id.asc())
    ).scalars().first()

    applicants: list[ApplicantOut] = []
    if room is not None and room.owner_id == current_user.id:
        rows = db.execute(
            select(RoomMember, User.username)
            .join(User, User.id == RoomMember.user_id)
            .where(
                RoomMember.room_id == room.id,
                RoomMember.status == MEMBER_STATUS_PENDING,
            )
            .order_by(RoomMember.id.asc())
        ).all()
        applicants = [
            ApplicantOut(
                member_id=member.id,
                user_id=member.user_id,
                username=username,
                status=member.status,
            )
            for member, username in rows
        ]

    base = _to_post_out(post, owner_username)
    return PostDetailOut(
        **base.model_dump(),
        room_id=room.id if room is not None else None,
        applicants=applicants,
    )


# response_model=None 是必需的：本文件启用了 from __future__ import annotations，
# `-> None` 在 __annotations__ 中会变成字符串 'None'，FastAPI 会把它当作真实 response_model，
# 从而触发「Status code 204 must not have a response body」断言。删掉这个参数会导致应用无法导入。
@router.delete("/{post_id}", status_code=204, response_model=None)
def delete_post(
    post_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """删除帖子；仅帖主可删，否则 403。已创建房间的帖子不可删除（409）。"""
    post = db.get(PartnerPost, post_id)
    if post is None:
        raise not_found("帖子不存在。")
    if post.owner_id != current_user.id:
        raise forbidden("仅帖主可删除该帖子。")

    room_exists = db.execute(
        select(Room.id).where(Room.post_id == post.id).limit(1)
    ).scalar_one_or_none()
    if room_exists is not None:
        raise conflict("该帖子已创建房间，无法删除。")

    db.delete(post)
    db.commit()
    return None
