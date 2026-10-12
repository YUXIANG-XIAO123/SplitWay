"""结算路由：触发结算（房主）/ 查询结算结果。"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import require_room_member, require_room_owner
from app.errors import conflict, not_found
from app.models.bill import Bill, BillShare
from app.models.room import MEMBER_STATUS_JOINED, ROOM_STATUS_SETTLED, Room, RoomMember
from app.models.settlement import Settlement, SettlementItem
from app.models.user import User
from app.schemas.settlement import SettlementCheck, SettlementItemOut, SettlementOut
from app.services.settlement import BillForSettlement, MemberForSettlement, compute_settlement

router = APIRouter()


def _build_settlement_out(db: Session, settlement: Settlement) -> SettlementOut:
    """由已存在的结算记录装配出参。"""
    rows = db.execute(
        select(SettlementItem, User.username)
        .join(User, User.id == SettlementItem.user_id)
        .where(SettlementItem.settlement_id == settlement.id)
        .order_by(SettlementItem.user_id.asc())
    ).all()

    # 反查 member_id（结算时可能存在已退出成员，取该用户在该房间的最新一条成员记录）。
    member_rows = db.execute(
        select(RoomMember.user_id, RoomMember.id)
        .where(RoomMember.room_id == settlement.room_id)
        .order_by(RoomMember.id.asc())
    ).all()
    member_id_by_user: dict[int, int] = {}
    for user_id, member_id in member_rows:
        member_id_by_user[user_id] = member_id

    items: list[SettlementItemOut] = []
    total_paid = 0
    total_share = 0
    for item, username in rows:
        total_paid += item.paid_cents
        total_share += item.share_cents
        items.append(
            SettlementItemOut(
                member_id=member_id_by_user.get(item.user_id, 0),
                user_id=item.user_id,
                username=username,
                paid_cents=item.paid_cents,
                share_cents=item.share_cents,
                net_cents=item.net_cents,
            )
        )

    return SettlementOut(
        room_id=settlement.room_id,
        settled_at=settlement.created_at,
        items=items,
        total_cents=total_paid,
        check=SettlementCheck(sum_share_equals_total=total_share == total_paid),
    )


@router.post("/{room_id}/settlement", response_model=SettlementOut)
def trigger_settlement(
    room_id: int,
    db: Session = Depends(get_db),
    room: Room = Depends(require_room_owner),
) -> SettlementOut:
    """触发结算；仅房主可调用。幂等：已结算则直接返回既有结果（B5）。

    前置条件：房间必须至少有一条账单。否则会生成一份"全员净额 0"的无意义结算，
    同时把房间置为 ``settled`` 只读 —— 而一条帖子只能有一个房间，等于把这条路彻底堵死。
    """
    existing = db.execute(
        select(Settlement).where(Settlement.room_id == room.id)
    ).scalar_one_or_none()
    if existing is not None:
        return _build_settlement_out(db, existing)

    # 防呆：零账单不允许结算。
    bill_count = db.execute(
        select(func.count()).select_from(Bill).where(Bill.room_id == room.id)
    ).scalar_one()
    if bill_count == 0:
        raise conflict("房间还没有账单，无需结算。请先记一笔账。")

    # 参与结算的成员：当前 joined 成员（含房主）。
    member_rows = db.execute(
        select(RoomMember, User.username)
        .join(User, User.id == RoomMember.user_id)
        .where(
            RoomMember.room_id == room.id,
            RoomMember.status == MEMBER_STATUS_JOINED,
        )
        .order_by(RoomMember.user_id.asc())
    ).all()
    members = [
        MemberForSettlement(member_id=member.id, user_id=member.user_id, username=username)
        for member, username in member_rows
    ]

    # 账单及分摊明细。
    bills = db.execute(
        select(Bill).where(Bill.room_id == room.id).order_by(Bill.id.asc())
    ).scalars().all()
    bills_for_settlement: list[BillForSettlement] = []
    for bill in bills:
        shares = db.execute(
            select(BillShare).where(BillShare.bill_id == bill.id)
        ).scalars().all()
        bills_for_settlement.append(
            BillForSettlement(
                payer_id=bill.payer_id,
                amount_cents=bill.amount_cents,
                shares={share.user_id: share.amount_cents for share in shares},
            )
        )

    lines, _total_cents, _check = compute_settlement(members, bills_for_settlement)

    settlement = Settlement(room_id=room.id)
    db.add(settlement)
    db.flush()
    for line in lines:
        db.add(
            SettlementItem(
                settlement_id=settlement.id,
                user_id=line.user_id,
                paid_cents=line.paid_cents,
                share_cents=line.share_cents,
                net_cents=line.net_cents,
            )
        )
    room.status = ROOM_STATUS_SETTLED
    db.commit()
    db.refresh(settlement)
    return _build_settlement_out(db, settlement)


@router.get("/{room_id}/settlement", response_model=SettlementOut)
def get_settlement(
    room_id: int,
    db: Session = Depends(get_db),
    _membership: RoomMember = Depends(require_room_member),
) -> SettlementOut:
    """查询结算结果；仅该房间 joined/owner 成员可见；未结算返回 404。"""
    settlement = db.execute(
        select(Settlement).where(Settlement.room_id == room_id)
    ).scalar_one_or_none()
    if settlement is None:
        raise not_found("该房间尚未结算。")
    return _build_settlement_out(db, settlement)
