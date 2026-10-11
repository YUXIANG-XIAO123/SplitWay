"""房间与成员路由：建房间 / 申请 / 审批 / 拒绝 / 退出 / 查询。"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.deps import get_current_user, get_room_or_404, require_room_member, require_room_owner
from app.errors import conflict, forbidden, not_found
from app.models.post import PartnerPost
from app.models.room import (
    ACTIVE_MEMBER_STATUSES,
    MEMBER_ROLE_MEMBER,
    MEMBER_ROLE_OWNER,
    MEMBER_STATUS_JOINED,
    MEMBER_STATUS_LEFT,
    MEMBER_STATUS_PENDING,
    MEMBER_STATUS_REJECTED,
    ROOM_STATUS_OPEN,
    ROOM_STATUS_SETTLED,
    Room,
    RoomMember,
)
from app.models.user import User
from app.schemas.room import JoinRequestOut, MemberOut, RoomCreate, RoomDetailOut, RoomOut

router = APIRouter()


def _to_member_out(member: RoomMember, username: str | None) -> MemberOut:
    """把成员 ORM 对象转为出参。"""
    return MemberOut(
        id=member.id,
        room_id=member.room_id,
        user_id=member.user_id,
        username=username,
        status=member.status,
        role=member.role,
        created_at=member.created_at,
    )


def _list_members(db: Session, room_id: int) -> list[MemberOut]:
    """列出房间全部成员记录（含历史），带用户名。"""
    rows = db.execute(
        select(RoomMember, User.username)
        .join(User, User.id == RoomMember.user_id)
        .where(RoomMember.room_id == room_id)
        .order_by(RoomMember.id.asc())
    ).all()
    return [_to_member_out(member, username) for member, username in rows]


def _joined_member_count(db: Session, room_id: int) -> int:
    """统计 joined 且非房主的成员数（房主不占名额）。"""
    stmt = (
        select(func.count())
        .select_from(RoomMember)
        .where(
            RoomMember.room_id == room_id,
            RoomMember.status == MEMBER_STATUS_JOINED,
            RoomMember.role != MEMBER_ROLE_OWNER,
        )
    )
    return int(db.execute(stmt).scalar_one())


@router.post("", status_code=201, response_model=RoomOut)
def create_room(
    payload: RoomCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Room:
    """基于搭子帖创建房间；仅帖主可建，创建者自动成为房主。"""
    post = db.get(PartnerPost, payload.post_id)
    if post is None:
        raise not_found("帖子不存在。")
    if post.owner_id != current_user.id:
        raise forbidden("仅帖主可创建房间。")

    existing = db.execute(
        select(Room).where(Room.post_id == post.id).order_by(Room.id.asc())
    ).scalars().first()
    if existing is not None:
        raise conflict("该帖子已存在房间。")

    room = Room(
        post_id=post.id,
        owner_id=current_user.id,
        status=ROOM_STATUS_OPEN,
        member_limit=settings.room_member_limit,
    )
    db.add(room)
    db.flush()  # 取得 room.id
    db.add(
        RoomMember(
            room_id=room.id,
            user_id=current_user.id,
            status=MEMBER_STATUS_JOINED,
            role=MEMBER_ROLE_OWNER,
        )
    )
    db.commit()
    db.refresh(room)
    return room


@router.get("", response_model=list[RoomOut])
def list_my_rooms(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Room]:
    """我参与的房间列表（有效成员记录：pending / joined）。"""
    stmt = (
        select(Room)
        .join(RoomMember, RoomMember.room_id == Room.id)
        .where(
            RoomMember.user_id == current_user.id,
            RoomMember.status.in_(ACTIVE_MEMBER_STATUSES),
        )
        .order_by(Room.id.desc())
    )
    return list(db.execute(stmt).scalars().all())


@router.get("/{room_id}", response_model=RoomDetailOut)
def get_room(
    room_id: int,
    db: Session = Depends(get_db),
    membership: RoomMember = Depends(require_room_member),
) -> RoomDetailOut:
    """房间详情；仅该房间 joined/owner 成员可见，否则 403（C1）。"""
    room = get_room_or_404(room_id, db)
    base = RoomOut.model_validate(room)
    return RoomDetailOut(**base.model_dump(), members=_list_members(db, room.id))


@router.get("/{room_id}/members", response_model=list[MemberOut])
def list_members(
    room_id: int,
    db: Session = Depends(get_db),
    _membership: RoomMember = Depends(require_room_member),
) -> list[MemberOut]:
    """房间成员列表；仅该房间 joined/owner 成员可见。"""
    return _list_members(db, room_id)


@router.post("/{room_id}/join-requests", status_code=201, response_model=JoinRequestOut)
def create_join_request(
    room_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MemberOut:
    """申请加入房间；重复申请返回 409。"""
    room = get_room_or_404(room_id, db)
    if room.status == ROOM_STATUS_SETTLED:
        raise conflict("房间已结算，无法申请加入。")
    if room.owner_id == current_user.id:
        raise conflict("你已是该房间房主。")

    active = db.execute(
        select(RoomMember).where(
            RoomMember.room_id == room.id,
            RoomMember.user_id == current_user.id,
            RoomMember.status.in_(ACTIVE_MEMBER_STATUSES),
        )
    ).scalar_one_or_none()
    if active is not None:
        raise conflict("你已提交申请或已是房间成员。")

    member = RoomMember(
        room_id=room.id,
        user_id=current_user.id,
        status=MEMBER_STATUS_PENDING,
        role=MEMBER_ROLE_MEMBER,
    )
    db.add(member)
    db.commit()
    db.refresh(member)
    return _to_member_out(member, current_user.username)


@router.post("/{room_id}/members/{member_id}/approve", response_model=MemberOut)
def approve_member(
    room_id: int,
    member_id: int,
    db: Session = Depends(get_db),
    _room: Room = Depends(require_room_owner),
) -> MemberOut:
    """审批通过申请；仅房主可调用（B6）。超员返回 409。"""
    member = db.get(RoomMember, member_id)
    if member is None or member.room_id != room_id:
        raise not_found("成员记录不存在。")
    if member.status != MEMBER_STATUS_PENDING:
        raise conflict("该申请当前不可审批。")

    if _joined_member_count(db, room_id) >= _room.member_limit:
        raise conflict("房间人数已达上限。")

    member.status = MEMBER_STATUS_JOINED
    db.commit()
    db.refresh(member)
    username = db.execute(
        select(User.username).where(User.id == member.user_id)
    ).scalar_one_or_none()
    return _to_member_out(member, username)


@router.post("/{room_id}/members/{member_id}/reject", response_model=MemberOut)
def reject_member(
    room_id: int,
    member_id: int,
    db: Session = Depends(get_db),
    _room: Room = Depends(require_room_owner),
) -> MemberOut:
    """拒绝申请；仅房主可调用，否则 403。"""
    member = db.get(RoomMember, member_id)
    if member is None or member.room_id != room_id:
        raise not_found("成员记录不存在。")
    if member.status != MEMBER_STATUS_PENDING:
        raise conflict("该申请当前不可处理。")

    member.status = MEMBER_STATUS_REJECTED
    db.commit()
    db.refresh(member)
    username = db.execute(
        select(User.username).where(User.id == member.user_id)
    ).scalar_one_or_none()
    return _to_member_out(member, username)


@router.post("/{room_id}/leave", response_model=MemberOut)
def leave_room(
    room_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MemberOut:
    """退出房间；仅本人可退出，房主不可退出（V1）。"""
    room = get_room_or_404(room_id, db)
    member = db.execute(
        select(RoomMember).where(
            RoomMember.room_id == room.id,
            RoomMember.user_id == current_user.id,
            RoomMember.status == MEMBER_STATUS_JOINED,
        )
    ).scalar_one_or_none()
    if member is None:
        raise conflict("你不是该房间的已加入成员。")
    if member.role == MEMBER_ROLE_OWNER:
        raise forbidden("房主不可退出房间。")

    member.status = MEMBER_STATUS_LEFT
    db.commit()
    db.refresh(member)
    return _to_member_out(member, current_user.username)
