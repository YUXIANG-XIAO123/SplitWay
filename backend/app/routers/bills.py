"""账单路由：新增 / 列表 / 删除。"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_room_or_404, require_room_member, require_room_owner
from app.errors import bad_request, conflict, forbidden, not_found
from app.models.bill import Bill, BillShare
from app.models.room import MEMBER_STATUS_JOINED, ROOM_STATUS_SETTLED, Room, RoomMember
from app.schemas.bill import BillCreate, BillOut
from app.services.split import split_equal

router = APIRouter()


@router.post("/{room_id}/bills", status_code=201, response_model=BillOut)
def create_bill(
    room_id: int,
    payload: BillCreate,
    db: Session = Depends(get_db),
    membership: RoomMember = Depends(require_room_member),
) -> Bill:
    """新增账单；仅 joined 成员可记账（B4）。已结算房间返回 409。"""
    room: Room = get_room_or_404(room_id, db)
    if room.status == ROOM_STATUS_SETTLED:
        raise conflict("房间已结算，账单只读。")

    participants = list(payload.participant_member_ids)
    if len(set(participants)) != len(participants):
        raise bad_request("participant_member_ids 存在重复成员。")

    # 参与分摊的成员必须全部是该房间的 joined 成员。
    member_rows = db.execute(
        select(RoomMember).where(
            RoomMember.id.in_(participants),
            RoomMember.room_id == room.id,
            RoomMember.status == MEMBER_STATUS_JOINED,
        )
    ).scalars().all()
    if {m.id for m in member_rows} != set(participants):
        raise forbidden("分摊人必须全部是该房间的 joined 成员。")

    participant_user_ids = [m.user_id for m in member_rows]

    # 付款人：默认操作者本人；否则必须为该房间 joined 成员。
    payer_id = payload.payer_id if payload.payer_id is not None else membership.user_id
    payer_is_member = db.execute(
        select(RoomMember.id).where(
            RoomMember.room_id == room.id,
            RoomMember.user_id == payer_id,
            RoomMember.status == MEMBER_STATUS_JOINED,
        )
    ).scalar_one_or_none()
    if payer_is_member is None:
        raise forbidden("付款人必须是该房间的 joined 成员。")

    shares = split_equal(payload.amount_cents, participant_user_ids)

    bill = Bill(
        room_id=room.id,
        payer_id=payer_id,
        amount_cents=payload.amount_cents,
        note=payload.note,
    )
    db.add(bill)
    db.flush()
    for user_id, amount_cents in shares.items():
        db.add(BillShare(bill_id=bill.id, user_id=user_id, amount_cents=amount_cents))
    db.commit()
    db.refresh(bill)
    return bill


@router.get("/{room_id}/bills", response_model=list[BillOut])
def list_bills(
    room_id: int,
    db: Session = Depends(get_db),
    _membership: RoomMember = Depends(require_room_member),
) -> list[Bill]:
    """账单列表（含分摊）；仅该房间 joined/owner 成员可见。"""
    stmt = select(Bill).where(Bill.room_id == room_id).order_by(Bill.id.asc())
    return list(db.execute(stmt).scalars().all())


# response_model=None 是必需的：本文件启用了 from __future__ import annotations，
# `-> None` 在 __annotations__ 中会变成字符串 'None'，FastAPI 会把它当作真实 response_model，
# 从而触发「Status code 204 must not have a response body」断言。删掉这个参数会导致应用无法导入。
@router.delete("/{room_id}/bills/{bill_id}", status_code=204, response_model=None)
def delete_bill(
    room_id: int,
    bill_id: int,
    db: Session = Depends(get_db),
    room: Room = Depends(require_room_owner),
) -> None:
    """删除账单；仅房主可删，已结算房间返回 409。"""
    if room.status == ROOM_STATUS_SETTLED:
        raise conflict("房间已结算，账单只读。")

    bill = db.get(Bill, bill_id)
    if bill is None or bill.room_id != room_id:
        raise not_found("账单不存在。")

    db.delete(bill)
    db.commit()
    return None
