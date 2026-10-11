"""pytest 全局装置：独立测试库 + FastAPI TestClient。

测试使用与开发库分离的 ``<dbname>_test`` 数据库，并复用应用的全部依赖覆盖点。
"""

from __future__ import annotations

import os
from collections.abc import Callable, Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

# 应用配置在导入时即读取环境变量，docker compose 已注入这些值。
BASE_DATABASE_URL = os.environ["DATABASE_URL"]
_base_url = make_url(BASE_DATABASE_URL)
TEST_DB_NAME = f"{_base_url.database}_test"

# 1) 确保独立测试库存在（连接到 postgres 维护库执行 CREATE DATABASE）。
_admin_engine = create_engine(
    _base_url.set(database="postgres"), isolation_level="AUTOCOMMIT", future=True
)
with _admin_engine.connect() as _conn:
    _exists = _conn.execute(
        text("SELECT 1 FROM pg_database WHERE datname = :name"), {"name": TEST_DB_NAME}
    ).scalar()
    if not _exists:
        _conn.execute(text(f'CREATE DATABASE "{TEST_DB_NAME}"'))
_admin_engine.dispose()

# 2) 建立指向测试库的引擎与会话工厂。
from app.db import Base, get_db  # noqa: E402
from app import models  # noqa: E402,F401  (注册全部表)
from app.main import app  # noqa: E402

TEST_ENGINE = create_engine(
    _base_url.set(database=TEST_DB_NAME), pool_pre_ping=True, future=True
)
TestingSessionLocal = sessionmaker(
    bind=TEST_ENGINE, autoflush=False, autocommit=False, future=True
)

Base.metadata.drop_all(bind=TEST_ENGINE)
Base.metadata.create_all(bind=TEST_ENGINE)


def _override_get_db() -> Iterator[Session]:
    """测试环境下的 get_db 覆盖。"""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = _override_get_db


_TABLES_TO_TRUNCATE = (
    "settlement_items, settlements, bill_shares, bills, "
    "room_members, rooms, partner_posts, users"
)


@pytest.fixture(autouse=True)
def _clean_database() -> Iterator[None]:
    """每个用例结束后清空全部表，保证用例互不污染。"""
    yield
    with TEST_ENGINE.begin() as conn:
        conn.execute(text(f"TRUNCATE TABLE {_TABLES_TO_TRUNCATE} RESTART IDENTITY CASCADE"))


@pytest.fixture
def client() -> Iterator[TestClient]:
    """FastAPI 测试客户端。"""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def make_user(client: TestClient) -> Callable[..., dict]:
    """返回一个"注册并登录"的工厂函数，产出 token 与请求头。"""

    def _make(username: str, password: str = "pass1234") -> dict:
        reg = client.post(
            "/api/auth/register", json={"username": username, "password": password}
        )
        assert reg.status_code == 201, reg.text
        login = client.post(
            "/api/auth/login", json={"username": username, "password": password}
        )
        assert login.status_code == 200, login.text
        body = login.json()
        return {
            "id": body["user"]["id"],
            "username": username,
            "password": password,
            "token": body["access_token"],
            "headers": {"Authorization": f"Bearer {body['access_token']}"},
        }

    return _make
