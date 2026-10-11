"""认证测试：注册 / 登录 / me。"""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_register_returns_created(client: TestClient) -> None:
    resp = client.post("/api/auth/register", json={"username": "alice", "password": "pass1234"})
    assert resp.status_code == 201
    body = resp.json()
    assert body["username"] == "alice"
    assert "password" not in body
    assert "password_hash" not in body


def test_register_duplicate_username_returns_409(client: TestClient) -> None:
    client.post("/api/auth/register", json={"username": "alice", "password": "pass1234"})
    resp = client.post("/api/auth/register", json={"username": "alice", "password": "other123"})
    assert resp.status_code == 409


def test_login_success(client: TestClient) -> None:
    client.post("/api/auth/register", json={"username": "bob", "password": "pass1234"})
    resp = client.post("/api/auth/login", json={"username": "bob", "password": "pass1234"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["user"]["username"] == "bob"


def test_login_wrong_password_returns_401(client: TestClient) -> None:
    client.post("/api/auth/register", json={"username": "bob", "password": "pass1234"})
    resp = client.post("/api/auth/login", json={"username": "bob", "password": "wrongpass"})
    assert resp.status_code == 401


def test_me_returns_current_user(client: TestClient, make_user) -> None:
    user = make_user("carol")
    resp = client.get("/api/auth/me", headers=user["headers"])
    assert resp.status_code == 200
    assert resp.json()["username"] == "carol"


def test_me_without_token_returns_401(client: TestClient) -> None:
    """C5：未认证访问被拒。"""
    resp = client.get("/api/auth/me")
    assert resp.status_code == 401


def test_me_with_invalid_token_returns_401(client: TestClient) -> None:
    resp = client.get("/api/auth/me", headers={"Authorization": "Bearer not.a.token"})
    assert resp.status_code == 401
