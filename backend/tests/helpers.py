"""测试辅助函数：快速搭建"帖子 + 房间 + 若干已加入成员"的场景。"""

from __future__ import annotations

from fastapi.testclient import TestClient


def create_post(client: TestClient, headers: dict, *, need_count: int = 5) -> dict:
    """创建一条搭子帖。"""
    resp = client.post(
        "/api/posts",
        headers=headers,
        json={"destination": "西安", "depart_date": "2026-11-01", "need_count": need_count},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def create_room(client: TestClient, headers: dict, post_id: int) -> dict:
    """基于帖子创建房间。"""
    resp = client.post("/api/rooms", headers=headers, json={"post_id": post_id})
    assert resp.status_code == 201, resp.text
    return resp.json()


def apply_and_approve(
    client: TestClient, owner_headers: dict, applicant_headers: dict, room_id: int
) -> int:
    """申请人申请加入 -> 房主审批通过，返回 member_id。"""
    req = client.post(f"/api/rooms/{room_id}/join-requests", headers=applicant_headers)
    assert req.status_code == 201, req.text
    member_id = req.json()["id"]
    resp = client.post(
        f"/api/rooms/{room_id}/members/{member_id}/approve", headers=owner_headers
    )
    assert resp.status_code == 200, resp.text
    return member_id


def room_member_ids(client: TestClient, headers: dict, room_id: int) -> dict[int, int]:
    """返回 {user_id: member_id} 映射（仅 joined/owner 成员）。"""
    resp = client.get(f"/api/rooms/{room_id}/members", headers=headers)
    assert resp.status_code == 200, resp.text
    result: dict[int, int] = {}
    for member in resp.json():
        if member["status"] == "joined":
            result[member["user_id"]] = member["id"]
    return result
