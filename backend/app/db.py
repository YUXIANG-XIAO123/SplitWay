"""数据库引擎与会话管理。

执行模型为同步（architecture.md D5）：FastAPI 会把 `def` 端点放入线程池，
因此这里统一使用同步 SQLAlchemy Session。
"""

from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings


class Base(DeclarativeBase):
    """所有 ORM 模型的声明式基类。"""


# pool_pre_ping 避免容器重启后拿到失效连接。
engine = create_engine(settings.database_url, pool_pre_ping=True, future=True)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def get_db() -> Iterator[Session]:
    """FastAPI 依赖：提供一个请求级别的数据库会话。

    Yields:
        Session: 请求结束后自动关闭的会话。
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
