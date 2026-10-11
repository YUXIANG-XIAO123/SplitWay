#!/usr/bin/env python3
"""C1：跨用户越权（IDOR）断言脚本，可重复执行。

U1 建房间/账务；U2 非成员，逐一访问 U1 的房间 / 成员 / 账单 / 结算资源，
全部必须返回 403。

用法：
    BASE_URL=http://localhost:8000 python scripts/test_idor.py

退出码 0 表示全部断言成立。
"""

from __future__ import annotations

import os
import sys
import time
import uuid

import httpx

BASE_URL = os.environ.get("BASE_URL", "http://localhost:8000").rstrip("/")


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _register_and_login(client: httpx.Client, username: str, password: str) -> str:
    """注册并登录，返回 token。"""
    reg = client.post("/api/auth/register", json={"username": username, "password": password})
    assert reg.status_code == 201, f"register failed: {reg.text}"
    login = client.post("/api/auth/login", json={"username": username, "password": password})
    assert login.status_code == 200, f"login failed: {login.text}"
    return login.json()["access_token"]


def _check(resp: httpx.Response, label: str) -> None:
    assert resp.status_code == 403, f"{label} 期望 403，实际 {resp.status_code}: {resp.text}"
    print(f"[ok] {label} -> 403")


def main() -> int:
    """执行 IDOR 断言；返回进程退出码。"""
    suffix = f"{int(time.time())}_{uuid.uuid4().hex[:8]}"
    password = "pass1234"
    with httpx.Client(base_url=BASE_URL, timeout=15.0) as client:
        u1 = _register_and_login(client, f"idor_u1_{suffix}", password)
        u2 = _register_and_login(client, f"idor_u2_{suffix}", password)

        post = client.post(
            "/api/posts",
            headers=_auth(u1),
            json={"destination": "北京", "depart_date": "2026-12-20", "need_count": 3},
        )
        assert post.status_code == 201, post.text
        post_id = post.json()["id"]

        room = client.post("/api/rooms", headers=_auth(u1), json={"post_id": post_id})
        assert room.status_code == 201, room.text
        room_id = room.json()["id"]

        members = client.get(f"/api/rooms/{room_id}/members", headers=_auth(u1))
        assert members.status_code == 200
        owner_member_id = members.json()[0]["id"]

        _check(client.get(f"/api/rooms/{room_id}", headers=_auth(u2)), "U2 读房间详情")
        _check(
            client.get(f"/api/rooms/{room_id}/members", headers=_auth(u2)), "U2 读成员列表"
        )
        _check(client.get(f"/api/rooms/{room_id}/bills", headers=_auth(u2)), "U2 读账单")
        _check(
            client.post(
                f"/api/rooms/{room_id}/bills",
                headers=_auth(u2),
                json={"amount_cents": 100, "participant_member_ids": [owner_member_id]},
            ),
            "U2 记账",
        )
        _check(
            client.get(f"/api/rooms/{room_id}/settlement", headers=_auth(u2)), "U2 读结算"
        )
        _check(
            client.post(f"/api/rooms/{room_id}/settlement", headers=_auth(u2)), "U2 触发结算"
        )
        _check(
            client.post(
                f"/api/rooms/{room_id}/members/{owner_member_id}/approve", headers=_auth(u2)
            ),
            "U2 越权审批",
        )
        _check(
            client.delete(f"/api/rooms/{room_id}/bills/1", headers=_auth(u2)), "U2 删账单"
        )

    print("IDOR PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
