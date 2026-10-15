"""结算测试：净额计算 / 幂等 / 结算后只读 / 权限。"""

from __future__ import annotations

import threading

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


def test_settlement_concurrent_calls_are_idempotent(
    client: TestClient, make_user
) -> None:
    """并发结算：两个请求同时进入时，都必须拿到 200，不能出现 500。

    回归用例。修复前的行为：两个请求都会查到"还没有结算"，然后都尝试 INSERT，
    其中一个撞 ``settlements.room_id`` 的唯一约束 → IntegrityError → **500**。
    ``settlements.room_id`` 的唯一约束只保证"最终不会有两行"，不保证"两个请求都成功"。

    注意：两个线程各用一个独立 TestClient，避免共用连接导致请求被串行化而测不到并发。
    """
    owner, _m2, _m3, room = _setup_settled_candidate(client, make_user)
    url = f"/api/rooms/{room['id']}/settlement"

    barrier = threading.Barrier(2)
    results: list[int] = []
    bodies: list[dict] = []
    lock = threading.Lock()

    def call() -> None:
        local = TestClient(client.app)
        barrier.wait(timeout=10)
        resp = local.post(url, headers=owner["headers"])
        with lock:
            results.append(resp.status_code)
            if resp.status_code == 200:
                bodies.append(resp.json())

    threads = [threading.Thread(target=call) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)

    assert sorted(results) == [200, 200], f"并发结算出现非 200：{results}"
    # 两次返回必须是同一份结算（同一时间戳），即真正的幂等
    assert len(bodies) == 2
    assert bodies[0]["settled_at"] == bodies[1]["settled_at"]
    assert bodies[0]["items"] == bodies[1]["items"]
    # 且库里只有一条结算记录
    got = client.get(url, headers=owner["headers"])
    assert got.status_code == 200
    assert got.json()["settled_at"] == bodies[0]["settled_at"]


def test_settlement_includes_member_who_left_after_billing(
    client: TestClient, make_user
) -> None:
    """记完账之后退出房间的成员，仍必须出现在结算结果里。

    回归用例。修复前的行为：结算参与者只取 ``status = joined``，于是
    - 已退出成员的已付 / 分摊被累加进字典却不输出 → **净额之和不为 0**；
    - 出参的 ``check`` 是按输出行求和的 → 把"分摊之和 == 账单总额"**误报为未通过**，
      看起来像数据损坏，其实只是漏了一行。

    正确口径：参与结算的人 = 当前 joined 成员 ∪ 所有账单里出现过的人（付款人或分摊人）。
    """
    owner = make_user("user1")
    m2 = make_user("user2")
    post = create_post(client, owner["headers"], need_count=5)
    room = create_room(client, owner["headers"], post["id"])
    apply_and_approve(client, owner["headers"], m2["headers"], room["id"])

    # owner 垫付 10000 分，owner 与 m2 各摊 5000
    member_ids = room_member_ids(client, owner["headers"], room["id"])
    created = client.post(
        f"/api/rooms/{room['id']}/bills",
        headers=owner["headers"],
        json={"amount_cents": 10000, "participant_member_ids": list(member_ids.values())},
    )
    assert created.status_code == 201, created.text

    # m2 在结算前退出
    left = client.post(f"/api/rooms/{room['id']}/leave", headers=m2["headers"])
    assert left.status_code == 200, left.text

    resp = client.post(f"/api/rooms/{room['id']}/settlement", headers=owner["headers"])
    assert resp.status_code == 200, resp.text
    body = resp.json()

    items = {item["user_id"]: item for item in body["items"]}
    assert m2["id"] in items, "已退出但参与过账务的成员必须仍出现在结算里"
    assert owner["id"] in items

    # 净额守恒：全员净额之和恒为 0
    assert sum(item["net_cents"] for item in body["items"]) == 0
    # owner 净应收 5000，m2 净应付 5000
    assert items[owner["id"]]["net_cents"] == 5000
    assert items[m2["id"]]["net_cents"] == -5000
    # check 不应因为漏行而误报
    assert body["check"]["sum_share_equals_total"] is True
    assert body["total_cents"] == 10000
