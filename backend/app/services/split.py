"""均分算法（最大余额法）。

V1 只做均分（D8）。全程整数分运算，不出现浮点（D7）。

在"均分"场景下所有成员的小数部分完全相同，最大余额法退化为
"按 userId 升序分配余数"，规则确定且可断言。
"""

from __future__ import annotations

from collections.abc import Iterable


def split_equal(amount_cents: int, user_ids: Iterable[int]) -> dict[int, int]:
    """把金额按人数均分，余数按 userId 升序逐个 +1 分。

    Args:
        amount_cents: 待分摊金额，单位：分，必须 > 0。
        user_ids: 参与分摊的用户 ID 集合，必须非空。

    Returns:
        形如 ``{user_id: amount_cents}`` 的映射，其值之和严格等于入参金额。

    Raises:
        ValueError: 金额非正、参与人为空或存在重复 user_id。
    """
    participants = list(user_ids)
    if amount_cents <= 0:
        raise ValueError("amount_cents 必须为正整数。")
    if not participants:
        raise ValueError("participant 不能为空。")
    if len(set(participants)) != len(participants):
        raise ValueError("participant 存在重复成员。")

    n = len(participants)
    base = amount_cents // n
    remainder = amount_cents % n

    ordered = sorted(participants)
    result: dict[int, int] = {}
    for index, user_id in enumerate(ordered):
        # 前 remainder 名（按 userId 升序）各多分 1 分。
        result[user_id] = base + (1 if index < remainder else 0)

    # 不变式：分摊之和必须等于账单金额。
    if sum(result.values()) != amount_cents:
        raise AssertionError("均分结果之和与账单金额不一致。")
    return result
