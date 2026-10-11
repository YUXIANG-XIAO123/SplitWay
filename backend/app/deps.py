"""FastAPI 依赖：身份解析与房间级权限。

硬约束：身份**只**来自 Authorization: Bearer <token>，服务端解析；
任何接口都不接受身份入参。
"""

from __future__ import annotations

from fastapi import Depends, Header
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.errors import forbidden, not_found, unauthorized
from app.models.room import MEMBER_ROLE_OWNER, MEMBER_STATUS_JOINED, Room, RoomMember
from app.models.user import User
from app.security import decode_access_token


def get_current_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    """从 Authorization 头解析当前用户。

    Args:
        authorization: 形如 ``Bearer <token>`` 的请求头。
        db: 数据库会话。

    Returns:
        当前登录用户。

    Raises:
        HTTPException: 401（无 token / token 无效 / 用户不存在）。
    """
    if not authorization:
        raise unauthorized()
    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer" or not parts[1].strip():
        raise unauthorized()
    token = parts[1].strip()
    try:
        user_id = decode_access_token(token)
    except Exception:
        # 不区分"过期/签名错误/格式错误"，一律 401，避免泄露细节。
        raise unauthorized()

    user = db.get(User, user_id)
    if user is None:
        raise unauthorized()
    return user


def get_room_or_404(room_id: int, db: Session) -> Room:
    """按主键取房间，不存在则 404。"""
    room = db.get(Room, room_id)
    if room is None:
        raise not_found("房间不存在。")
    return room


def get_active_membership(db: Session, room_id: int, user_id: int) -> RoomMember | None:
    """返回某用户在某房间的 joined 成员记录（无则 None）。"""
    stmt = select(RoomMember).where(
        RoomMember.room_id == room_id,
        RoomMember.user_id == user_id,
        RoomMember.status == MEMBER_STATUS_JOINED,
    )
    return db.execute(stmt).scalar_one_or_none()


def require_room_member(
    room_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> RoomMember:
    """要求当前用户是该房间的 joined 成员（含房主）。

    Raises:
        HTTPException: 404 房间不存在；403 非 joined 成员（C1）。
    """
    room = get_room_or_404(room_id, db)
    membership = get_active_membership(db, room.id, user.id)
    if membership is None:
        raise forbidden("你不是该房间的成员。")
    return membership


def require_room_owner(
    room_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Room:
    """要求当前用户是该房间的房主。

    Raises:
        HTTPException: 404 房间不存在；403 非房主（B6）。
    """
    room = get_room_or_404(room_id, db)
    if room.owner_id != user.id:
        raise forbidden("仅房主可执行该操作。")
    return room


def is_room_owner(room: Room, user_id: int) -> bool:
    """判断某用户是否为房间房主。"""
    return room.owner_id == user_id


def is_owner_membership(member: RoomMember) -> bool:
    """判断某成员记录是否为房主记录。"""
    return member.role == MEMBER_ROLE_OWNER
