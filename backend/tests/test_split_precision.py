"""B3：金额精度（除不尽场景）。

断言要点：
- 3 人均分 100.00 元（10000 分），三人应付之和 == 10000。
- 全程整数分运算，无浮点误差。
- 取整规则固定：余数按 userId 升序逐个 +1 分。
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.services.split import split_equal
from tests.helpers import apply_and_approve, create_post, create_room, room_member_ids


def test_split_equal_three_way_remainder() -> None:
    """纯函数层：10000 分 3 人等分。"""
    result = split_equal(10000, [1, 2, 3])
    assert result == {1: 3334, 2: 3333, 3: 3333}
    assert sum(result.values()) == 10000


def test_split_equal_remainder_ordering_is_deterministic() -> None:
    """余数按 userId 升序分配，与传入顺序无关。"""
    assert split_equal(100, [3, 1, 2]) == split_equal(100, [1, 2, 3])
    assert split_equal(100, [1, 2, 3]) == {1: 34, 2: 33, 3: 33}


def test_split_equal_single_cent() -> None:
    """1 分给 3 人：仅最小 userId 得到 1 分，其余 0 分，合计仍为 1。"""
    result = split_equal(1, [7, 5, 9])
    assert result == {5: 1, 7: 0, 9: 0}
    assert sum(result.values()) == 1


def test_split_equal_no_float_error_over_many_amounts() -> None:
    """遍历一批金额，验证整数不变式始终成立且无浮点参与。"""
    participants = [1, 2, 3, 4, 5, 6, 7]
    for amount in range(1, 200):
        result = split_equal(amount, participants)
        assert sum(result.values()) == amount
        assert all(isinstance(value, int) for value in result.values())


def test_bill_split_sum_equals_amount_via_api(client: TestClient, make_user) -> None:
    """API 层：3 人房间账单合计 10000 分，分摊之和 == 10000。"""
    owner = make_user("user1")
    m2 = make_user("user2")
    m3 = make_user("user3")
    post = create_post(client, owner["headers"], need_count=5)
    room = create_room(client, owner["headers"], post["id"])
    apply_and_approve(client, owner["headers"], m2["headers"], room["id"])
    apply_and_approve(client, owner["headers"], m3["headers"], room["id"])
    member_ids = room_member_ids(client, owner["headers"], room["id"])

    created = client.post(
        f"/api/rooms/{room['id']}/bills",
        headers=owner["headers"],
        json={"amount_cents": 10000, "participant_member_ids": list(member_ids.values())},
    )
    assert created.status_code == 201
    bill = created.json()
    shares = {share["user_id"]: share["amount_cents"] for share in bill["shares"]}
    # user_id 1/2/3 依次获得 3334/3333/3333
    assert shares == {owner["id"]: 3334, m2["id"]: 3333, m3["id"]: 3333}
    assert sum(shares.values()) == 10000


def test_settlement_sum_share_equals_total_via_api(client: TestClient, make_user) -> None:
    """B3（端到端）：结算结果 check 字段为真。"""
    owner = make_user("user1")
    m2 = make_user("user2")
    m3 = make_user("user3")
    post = create_post(client, owner["headers"], need_count=5)
    room = create_room(client, owner["headers"], post["id"])
    apply_and_approve(client, owner["headers"], m2["headers"], room["id"])
    apply_and_approve(client, owner["headers"], m3["headers"], room["id"])
    member_ids = room_member_ids(client, owner["headers"], room["id"])
    client.post(
        f"/api/rooms/{room['id']}/bills",
        headers=owner["headers"],
        json={"amount_cents": 10000, "participant_member_ids": list(member_ids.values())},
    )

    resp = client.post(f"/api/rooms/{room['id']}/settlement", headers=owner["headers"])
    assert resp.status_code == 200
    body = resp.json()
    assert body["check"]["sum_share_equals_total"] is True
    assert sum(item["share_cents"] for item in body["items"]) == 10000
