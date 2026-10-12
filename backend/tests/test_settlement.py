"""结算测试：净额计算 / 幂等 / 结算后只读 / 权限。"""

from __future__ import annotations

from fastapi.testclient import TestClient

from tests.helpers import apply_and_approve, create_post, create_room, room_member_ids


def _setup_settled_candidate(client: TestClient, make_user) -> tuple[dict, dict, dict, dict]:
    """建立 3 名 joined 成员 + 一条 10000 分的账单，返回 (owner, m2, m3, room)。"""
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
    assert created.status_code == 201, created.text
    return owner, m2, m3, room


def test_settlement_computes_net_amounts(client: TestClient, make_user) -> None:
    owner, m2, m3, room = _setup_settled_candidate(client, make_user)
    resp = client.post(f"/api/rooms/{room['id']}/settlement", headers=owner["headers"])
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["total_cents"] == 10000
    assert body["check"]["sum_share_equals_total"] is True
    assert len(body["items"]) == 3
    # 三个人的净额之和为 0（纯整数加减）
    assert sum(item["net_cents"] for item in body["items"]) == 0
    # 付款人应净应收
    payer_item = next(item for item in body["items"] if item["user_id"] == owner["id"])
    assert payer_item["paid_cents"] == 10000
    assert payer_item["net_cents"] == payer_item["paid_cents"] - payer_item["share_cents"]


def test_settlement_is_idempotent(client: TestClient, make_user) -> None:
    """B5：连续两次结算，结果不变，不新建记录。"""
    owner, _m2, _m3, room = _setup_settled_candidate(client, make_user)
    first = client.post(f"/api/rooms/{room['id']}/settlement", headers=owner["headers"])
    second = client.post(f"/api/rooms/{room['id']}/settlement", headers=owner["headers"])
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["settled_at"] == second.json()["settled_at"]
    assert first.json()["items"] == second.json()["items"]


def test_settled_room_rejects_new_bill(client: TestClient, make_user) -> None:
    owner, _m2, _m3, room = _setup_settled_candidate(client, make_user)
    client.post(f"/api/rooms/{room['id']}/settlement", headers=owner["headers"])
    member_ids = room_member_ids(client, owner["headers"], room["id"])
    resp = client.post(
        f"/api/rooms/{room['id']}/bills",
        headers=owner["headers"],
        json={"amount_cents": 100, "participant_member_ids": list(member_ids.values())},
    )
    assert resp.status_code == 409


def test_only_owner_can_trigger_settlement(client: TestClient, make_user) -> None:
    owner, m2, _m3, room = _setup_settled_candidate(client, make_user)
    resp = client.post(f"/api/rooms/{room['id']}/settlement", headers=m2["headers"])
    assert resp.status_code == 403
    # 未结算
    assert (
        client.get(f"/api/rooms/{room['id']}/settlement", headers=owner["headers"]).status_code
        == 404
    )


def test_get_settlement_before_settlement_returns_404(client: TestClient, make_user) -> None:
    owner, _m2, _m3, room = _setup_settled_candidate(client, make_user)
    resp = client.get(f"/api/rooms/{room['id']}/settlement", headers=owner["headers"])
    assert resp.status_code == 404


def test_settlement_requires_at_least_one_bill(client: TestClient, make_user) -> None:
    """防呆：零账单不允许结算。

    否则会生成一份"全员净额 0"的无意义结算，同时把房间锁成 settled 只读；
    而一条帖子只能有一个房间（create_room 对同帖返回 409），等于把这条路彻底堵死。
    """
    owner = make_user("user1")
    m2 = make_user("user2")
    post = create_post(client, owner["headers"], need_count=5)
    room = create_room(client, owner["headers"], post["id"])
    apply_and_approve(client, owner["headers"], m2["headers"], room["id"])

    # 一条账单都没有 → 拒绝
    resp = client.post(f"/api/rooms/{room['id']}/settlement", headers=owner["headers"])
    assert resp.status_code == 409, resp.text
    assert "账单" in resp.json()["detail"]["message"]

    # 房间没有被锁死：仍可记账
    member_ids = room_member_ids(client, owner["headers"], room["id"])
    created = client.post(
        f"/api/rooms/{room['id']}/bills",
        headers=owner["headers"],
        json={"amount_cents": 10000, "participant_member_ids": list(member_ids.values())},
    )
    assert created.status_code == 201, created.text

    # 记了账单之后就能正常结算
    ok = client.post(f"/api/rooms/{room['id']}/settlement", headers=owner["headers"])
    assert ok.status_code == 200, ok.text
    assert ok.json()["total_cents"] == 10000
