#!/usr/bin/env python3
"""B2：端到端链路脚本。

用两个独立账号 U1 / U2 走完整链路：
注册 -> 登录 -> 发帖 -> 建房间 -> 申请 -> 审批 -> 记账 -> 结算。

用法（在容器内或本机有 httpx 的环境）：
    BASE_URL=http://localhost:8000 python scripts/e2e_link.py

退出码 0 表示链路全部通过。
"""

from __future__ import annotations

import os
import sys
import time
import uuid

import httpx

BASE_URL = os.environ.get("BASE_URL", "http://localhost:8000").rstrip("/")


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _register_and_login(client: httpx.Client, username: str, password: str) -> tuple[int, str]:
    """注册并登录，返回 (user_id, token)。"""
    reg = client.post("/api/auth/register", json={"username": username, "password": password})
    assert reg.status_code == 201, f"register failed: {reg.status_code} {reg.text}"
    user_id = reg.json()["id"]

    login = client.post("/api/auth/login", json={"username": username, "password": password})
    assert login.status_code == 200, f"login failed: {login.status_code} {login.text}"
    body = login.json()
    return user_id, body["access_token"]


def main() -> int:
    """执行完整链路；返回进程退出码。"""
    suffix = f"{int(time.time())}_{uuid.uuid4().hex[:8]}"
    u1_name = f"e2e_u1_{suffix}"
    u2_name = f"e2e_u2_{suffix}"
    password = "pass1234"

    with httpx.Client(base_url=BASE_URL, timeout=15.0) as client:
        u1_id, u1_token = _register_and_login(client, u1_name, password)
        u2_id, u2_token = _register_and_login(client, u2_name, password)
        assert u1_token != u2_token, "两个账号的 token 必须互相独立"
        print(f"[ok] 注册并登录：u1={u1_id} u2={u2_id}")

        # U1 发帖
        post = client.post(
            "/api/posts",
            headers=_auth_headers(u1_token),
            json={
                "destination": "上海",
                "depart_date": "2026-12-01",
                "need_count": 3,
                "note": "外滩跨年",
            },
        )
        assert post.status_code == 201, f"create post failed: {post.text}"
        post_id = post.json()["id"]
        print(f"[ok] U1 发帖 post_id={post_id}")

        # U1 建房间
        room = client.post(
            "/api/rooms", headers=_auth_headers(u1_token), json={"post_id": post_id}
        )
        assert room.status_code == 201, f"create room failed: {room.text}"
        room_id = room.json()["id"]
        print(f"[ok] U1 建房间 room_id={room_id}")

        # U2 申请加入
        join = client.post(
            f"/api/rooms/{room_id}/join-requests", headers=_auth_headers(u2_token)
        )
        assert join.status_code == 201, f"join failed: {join.text}"
        member_id = join.json()["id"]
        print(f"[ok] U2 申请加入 member_id={member_id}")

        # U1 审批通过
        approve = client.post(
            f"/api/rooms/{room_id}/members/{member_id}/approve",
            headers=_auth_headers(u1_token),
        )
        assert approve.status_code == 200, f"approve failed: {approve.text}"
        assert approve.json()["status"] == "joined"
        print("[ok] U1 审批通过，U2 成为 joined 成员")

        # 成员列表（取 member_id 供记账分摊使用）
        members = client.get(
            f"/api/rooms/{room_id}/members", headers=_auth_headers(u1_token)
        )
        assert members.status_code == 200, members.text
        joined_member_ids = [
            member["id"] for member in members.json() if member["status"] == "joined"
        ]
        assert len(joined_member_ids) == 2, "应有 2 名 joined 成员（房主 + U2）"

        # U1 记账：100.00 元，两人均分
        bill = client.post(
            f"/api/rooms/{room_id}/bills",
            headers=_auth_headers(u1_token),
            json={
                "amount_cents": 10000,
                "note": "酒店",
                "participant_member_ids": joined_member_ids,
            },
        )
        assert bill.status_code == 201, f"create bill failed: {bill.text}"
        assert sum(share["amount_cents"] for share in bill.json()["shares"]) == 10000
        print("[ok] U1 记账 10000 分，分摊之和 == 10000")

        # U1 结算
        settlement = client.post(
            f"/api/rooms/{room_id}/settlement", headers=_auth_headers(u1_token)
        )
        assert settlement.status_code == 200, f"settlement failed: {settlement.text}"
        body = settlement.json()
        assert body["check"]["sum_share_equals_total"] is True
        assert sum(item["share_cents"] for item in body["items"]) == 10000
        print(f"[ok] U1 结算：total={body['total_cents']} check={body['check']}")

        # 幂等：再次结算结果不变
        again = client.post(
            f"/api/rooms/{room_id}/settlement", headers=_auth_headers(u1_token)
        )
        assert again.status_code == 200
        assert again.json()["settled_at"] == body["settled_at"]
        print("[ok] 二次结算幂等")

    print("E2E PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
