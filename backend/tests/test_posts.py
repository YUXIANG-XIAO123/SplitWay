"""搭子帖测试：发帖 / 列表 / 详情 / 删除权限。"""

from __future__ import annotations

from fastapi.testclient import TestClient

from tests.helpers import apply_and_approve, create_room, room_member_ids


def _create_post(client: TestClient, headers: dict, *, need_count: int = 3) -> dict:
    resp = client.post(
        "/api/posts",
        headers=headers,
        json={
            "destination": "杭州",
            "depart_date": "2026-10-01",
            "need_count": need_count,
            "note": "看西湖",
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_create_post(client: TestClient, make_user) -> None:
    user = make_user("user1")
    post = _create_post(client, user["headers"])
    assert post["owner_id"] == user["id"]
    assert post["status"] == "open"
    assert post["need_count"] == 3


def test_create_post_rejects_need_count_below_two(client: TestClient, make_user) -> None:
    user = make_user("user1")
    resp = client.post(
        "/api/posts",
        headers=user["headers"],
        json={"destination": "杭州", "depart_date": "2026-10-01", "need_count": 1},
    )
    assert resp.status_code == 422


def test_list_posts_pagination(client: TestClient, make_user) -> None:
    user = make_user("user1")
    for i in range(3):
        _create_post(client, user["headers"], need_count=2 + i)
    resp = client.get("/api/posts", headers=user["headers"], params={"page": 1, "size": 2})
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 3
    assert len(body["items"]) == 2


def test_get_post_detail(client: TestClient, make_user) -> None:
    user = make_user("user1")
    post = _create_post(client, user["headers"])
    resp = client.get(f"/api/posts/{post['id']}", headers=user["headers"])
    assert resp.status_code == 200
    assert resp.json()["id"] == post["id"]


def test_delete_post_by_owner(client: TestClient, make_user) -> None:
    user = make_user("user1")
    post = _create_post(client, user["headers"])
    resp = client.delete(f"/api/posts/{post['id']}", headers=user["headers"])
    assert resp.status_code == 204
    assert client.get(f"/api/posts/{post['id']}", headers=user["headers"]).status_code == 404


def test_delete_post_by_non_owner_returns_403(client: TestClient, make_user) -> None:
    owner = make_user("user1")
    other = make_user("user2")
    post = _create_post(client, owner["headers"])
    resp = client.delete(f"/api/posts/{post['id']}", headers=other["headers"])
    assert resp.status_code == 403
    # 帖子仍然存在
    assert client.get(f"/api/posts/{post['id']}", headers=owner["headers"]).status_code == 200


def _post_with_room(client: TestClient, owner_headers: dict, other_headers: dict) -> tuple[dict, dict]:
    """建帖 + 建房 + 审批一名成员，返回 (post, room)。"""
    post = _create_post(client, owner_headers)
    room = create_room(client, owner_headers, post["id"])
    apply_and_approve(client, owner_headers, other_headers, room["id"])
    return post, room


def test_delete_post_with_empty_room_cascades(client: TestClient, make_user) -> None:
    """空房间（0 账单、未结算）随帖子一并删除，成员记录级联清除。

    这是"建错房间想重来"的正常出路——旧的"有房间就一律 409"把这条路堵死了。
    """
    owner = make_user("user1")
    other = make_user("user2")
    post, room = _post_with_room(client, owner["headers"], other["headers"])

    resp = client.delete(f"/api/posts/{post['id']}", headers=owner["headers"])
    assert resp.status_code == 204, resp.text

    # 帖子没了
    assert client.get(f"/api/posts/{post['id']}", headers=owner["headers"]).status_code == 404
    # 房间也没了：房主与成员的房间列表里都查不到
    for user in (owner, other):
        ids = [r["id"] for r in client.get("/api/rooms", headers=user["headers"]).json()]
        assert room["id"] not in ids


def test_delete_post_with_bills_returns_409(client: TestClient, make_user) -> None:
    """房间已有账单 → 拒绝删除（保护账目）。"""
    owner = make_user("user1")
    other = make_user("user2")
    post, room = _post_with_room(client, owner["headers"], other["headers"])
    member_ids = room_member_ids(client, owner["headers"], room["id"])
    created = client.post(
        f"/api/rooms/{room['id']}/bills",
        headers=owner["headers"],
        json={"amount_cents": 100, "participant_member_ids": list(member_ids.values())},
    )
    assert created.status_code == 201, created.text

    resp = client.delete(f"/api/posts/{post['id']}", headers=owner["headers"])
    assert resp.status_code == 409, resp.text
    # 帖子与房间都还在
    assert client.get(f"/api/posts/{post['id']}", headers=owner["headers"]).status_code == 200


def test_delete_post_with_settled_room_returns_409(client: TestClient, make_user) -> None:
    """房间已结算 → 拒绝删除（保护账目）。

    覆盖 ``room.status == settled`` 这一支；该分支对"防呆上线前就已结算的空房间"是必要的兜底。
    """
    owner = make_user("user1")
    other = make_user("user2")
    post, room = _post_with_room(client, owner["headers"], other["headers"])
    member_ids = room_member_ids(client, owner["headers"], room["id"])
    client.post(
        f"/api/rooms/{room['id']}/bills",
        headers=owner["headers"],
        json={"amount_cents": 100, "participant_member_ids": list(member_ids.values())},
    )
    settled = client.post(f"/api/rooms/{room['id']}/settlement", headers=owner["headers"])
    assert settled.status_code == 200, settled.text

    resp = client.delete(f"/api/posts/{post['id']}", headers=owner["headers"])
    assert resp.status_code == 409, resp.text
    assert client.get(f"/api/posts/{post['id']}", headers=owner["headers"]).status_code == 200
