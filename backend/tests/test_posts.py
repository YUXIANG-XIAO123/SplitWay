"""搭子帖测试：发帖 / 列表 / 详情 / 删除权限。"""

from __future__ import annotations

from fastapi.testclient import TestClient


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
