"""结算净额计算（纯整数加减）。"""

from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Iterable

from app.services.split import split_equal  # noqa: F401  (统一从 services 暴露)


@dataclass(frozen=True)
class MemberForSettlement:
    """参与结算的一个房间成员。"""

    member_id: int
    user_id: int
    username: str


@dataclass(frozen=True)
class BillForSettlement:
    """参与结算的一条账单：付款人 + 分摊明细。"""

    payer_id: int
    amount_cents: int
    shares: dict[int, int]


@dataclass(frozen=True)
class SettlementLine:
    """结算结果里的一行。"""

    member_id: int
    user_id: int
    username: str
    paid_cents: int
    share_cents: int
    net_cents: int


def compute_settlement(
    members: Iterable[MemberForSettlement],
    bills: Iterable[BillForSettlement],
) -> tuple[list[SettlementLine], int, bool]:
    """计算每个成员的应付/应收。

    paid_cents[user]  = 该用户作为 payer 的账单金额之和
    share_cents[user] = 该用户在所有分摊明细中的金额之和
    net_cents[user]   = paid_cents - share_cents

    结算阶段是纯整数加减，不产生任何余数。

    Args:
        members: 房间成员集合（用于保证每人一行，即使无账单也输出 0）。
        bills: 房间账单集合。

    Returns:
        ``(lines, total_cents, sum_share_equals_total)``：
        - lines: 按 user_id 升序的结算行；
        - total_cents: 账单总额（分）；
        - sum_share_equals_total: 分摊之和是否等于账单总额（不变式，B3）。
    """
    member_list = sorted(members, key=lambda m: m.user_id)

    paid: dict[int, int] = {m.user_id: 0 for m in member_list}
    share: dict[int, int] = {m.user_id: 0 for m in member_list}
    total_cents = 0
    total_shares = 0

    for bill in bills:
        total_cents += bill.amount_cents
        # 付款人若不在成员集合中，也纳入统计（防御性：确保 sum 不变式成立）。
        paid[bill.payer_id] = paid.get(bill.payer_id, 0) + bill.amount_cents
        for user_id, amount in bill.shares.items():
            share[user_id] = share.get(user_id, 0) + amount
            total_shares += amount

    lines: list[SettlementLine] = []
    for member in member_list:
        paid_cents = paid.get(member.user_id, 0)
        share_cents = share.get(member.user_id, 0)
        lines.append(
            SettlementLine(
                member_id=member.member_id,
                user_id=member.user_id,
                username=member.username,
                paid_cents=paid_cents,
                share_cents=share_cents,
                net_cents=paid_cents - share_cents,
            )
        )

    return lines, total_cents, total_shares == total_cents
