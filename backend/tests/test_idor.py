"""C1：跨用户越权断言（IDOR）。

U1 拥有房间；U2 不是该房间成员。U2 访问 U1 的房间 / 成员 / 账单 / 结算资源，
全部必须返回 403。断言可重复执行且结果稳定。
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from tests.helpers import create_post, create_room, room_member_ids


def _run_idor_assertions(client: TestClient, u1: dict, u2: dict) -> None:
    post = create_post(client, u1["headers"], need_count=5)
    room = create_room(client, u1["headers"], post["id"])
    room_id = room["id"]
    u1_headers = u1["headers"]
    u2_headers = u2["headers"]
    owner_member_id = room_member_ids(client, u1_headers, room_id)[u1["id"]]

    # 房间本身
    assert client.get(f"/api/rooms/{room_id}", headers=u2_headers).status_code == 403
    assert client.get(f"/api/rooms/{room_id}/members", headers=u2_headers).status_code == 403
    # 账单读取与写入
    assert client.get(f"/api/rooms/{room_id}/bills", headers=u2_headers).status_code == 403
    assert (
        client.post(
            f"/api/rooms/{room_id}/bills",
            headers=u2_headers,
            json={"amount_cents": 100, "participant_member_ids": [owner_member_id]},
        ).status_code
        == 403
    )
    # 结算读取与触发
    assert client.get(f"/api/rooms/{room_id}/settlement", headers=u2_headers).status_code == 403
    assert (
        client.post(f"/api/rooms/{room_id}/settlement", headers=u2_headers).status_code == 403
    )
    # 非房主审批
    assert (
        client.post(
            f"/api/rooms/{room_id}/members/{owner_member_id}/approve", headers=u2_headers
        ).status_code
        == 403
    )
    # 删除他人账单（账单不存在也应先被房主校验拦截为 403）
    assert (
        client.delete(f"/api/rooms/{room_id}/bills/1", headers=u2_headers).status_code == 403
    )


def test_idor_cross_user_access_returns_403(client: TestClient, make_user) -> None:
    u1 = make_user("idor_u1")
    u2 = make_user("idor_u2")
    _run_idor_assertions(client, u1, u2)


def test_idor_assertions_are_replayable(client: TestClient, make_user) -> None:
    """同一断言集重复执行两次，结果稳定（可重放）。"""
    u1 = make_user("idor_replay_u1")
    u2 = make_user("idor_replay_u2")
    _run_idor_assertions(client, u1, u2)
    _run_idor_assertions(client, u1, u2)
