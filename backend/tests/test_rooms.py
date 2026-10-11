"""房间与成员测试：建房间 / 申请 / 审批 / 拒绝 / 退出 / 权限。"""

from __future__ import annotations

from fastapi.testclient import TestClient


def _create_post(client: TestClient, headers: dict, need_count: int = 3) -> dict:
    resp = client.post(
        "/api/posts",
        headers=headers,
        json={
            "destination": "成都",
            "depart_date": "2026-10-05",
            "need_count": need_count,
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _create_room(client: TestClient, headers: dict, post_id: int) -> dict:
    resp = client.post("/api/rooms", headers=headers, json={"post_id": post_id})
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_create_room_only_by_post_owner(client: TestClient, make_user) -> None:
    owner = make_user("user1")
    other = make_user("user2")
    post = _create_post(client, owner["headers"])

    resp = client.post("/api/rooms", headers=other["headers"], json={"post_id": post["id"]})
    assert resp.status_code == 403

    room = _create_room(client, owner["headers"], post["id"])
    assert room["owner_id"] == owner["id"]
    assert room["status"] == "open"


def test_owner_is_joined_member(client: TestClient, make_user) -> None:
    owner = make_user("user1")
    post = _create_post(client, owner["headers"])
    room = _create_room(client, owner["headers"], post["id"])
    resp = client.get(f"/api/rooms/{room['id']}/members", headers=owner["headers"])
    assert resp.status_code == 200
    members = resp.json()
    assert len(members) == 1
    assert members[0]["role"] == "owner"
    assert members[0]["status"] == "joined"


def test_join_request_and_duplicate_conflict(client: TestClient, make_user) -> None:
    owner = make_user("user1")
    applicant = make_user("user2")
    post = _create_post(client, owner["headers"])
    room = _create_room(client, owner["headers"], post["id"])

    first = client.post(f"/api/rooms/{room['id']}/join-requests", headers=applicant["headers"])
    assert first.status_code == 201
    assert first.json()["status"] == "pending"

    second = client.post(f"/api/rooms/{room['id']}/join-requests", headers=applicant["headers"])
    assert second.status_code == 409


def test_approve_by_owner_makes_member_joined(client: TestClient, make_user) -> None:
    owner = make_user("user1")
    applicant = make_user("user2")
    post = _create_post(client, owner["headers"])
    room = _create_room(client, owner["headers"], post["id"])
    req = client.post(f"/api/rooms/{room['id']}/join-requests", headers=applicant["headers"])
    member_id = req.json()["id"]

    resp = client.post(
        f"/api/rooms/{room['id']}/members/{member_id}/approve", headers=owner["headers"]
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "joined"


def test_approve_by_non_owner_returns_403(client: TestClient, make_user) -> None:
    """B6：非房主不能审批。"""
    owner = make_user("user1")
    applicant = make_user("user2")
    intruder = make_user("user3")
    post = _create_post(client, owner["headers"])
    room = _create_room(client, owner["headers"], post["id"])
    # u3 先成为 joined 成员，再尝试审批
    req3 = client.post(f"/api/rooms/{room['id']}/join-requests", headers=intruder["headers"])
    client.post(
        f"/api/rooms/{room['id']}/members/{req3.json()['id']}/approve",
        headers=owner["headers"],
    )
    req2 = client.post(f"/api/rooms/{room['id']}/join-requests", headers=applicant["headers"])
    member_id = req2.json()["id"]

    resp = client.post(
        f"/api/rooms/{room['id']}/members/{member_id}/approve", headers=intruder["headers"]
    )
    assert resp.status_code == 403
    # 状态不变
    members = client.get(f"/api/rooms/{room['id']}/members", headers=owner["headers"]).json()
    target = next(m for m in members if m["id"] == member_id)
    assert target["status"] == "pending"


def test_reject_by_owner(client: TestClient, make_user) -> None:
    owner = make_user("user1")
    applicant = make_user("user2")
    post = _create_post(client, owner["headers"])
    room = _create_room(client, owner["headers"], post["id"])
    req = client.post(f"/api/rooms/{room['id']}/join-requests", headers=applicant["headers"])
    resp = client.post(
        f"/api/rooms/{room['id']}/members/{req.json()['id']}/reject", headers=owner["headers"]
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "rejected"


def test_member_can_leave_but_owner_cannot(client: TestClient, make_user) -> None:
    owner = make_user("user1")
    member = make_user("user2")
    post = _create_post(client, owner["headers"])
    room = _create_room(client, owner["headers"], post["id"])
    req = client.post(f"/api/rooms/{room['id']}/join-requests", headers=member["headers"])
    client.post(
        f"/api/rooms/{room['id']}/members/{req.json()['id']}/approve", headers=owner["headers"]
    )

    left = client.post(f"/api/rooms/{room['id']}/leave", headers=member["headers"])
    assert left.status_code == 200
    assert left.json()["status"] == "left"

    owner_leave = client.post(f"/api/rooms/{room['id']}/leave", headers=owner["headers"])
    assert owner_leave.status_code == 403


def test_room_detail_requires_membership(client: TestClient, make_user) -> None:
    owner = make_user("user1")
    outsider = make_user("user2")
    post = _create_post(client, owner["headers"])
    room = _create_room(client, owner["headers"], post["id"])

    assert client.get(f"/api/rooms/{room['id']}", headers=owner["headers"]).status_code == 200
    assert (
        client.get(f"/api/rooms/{room['id']}", headers=outsider["headers"]).status_code == 403
    )
