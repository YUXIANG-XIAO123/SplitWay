"""数据库 engine / Session（#1）。

事务边界写在 service 层（development-handbook.md §5），本模块只提供
engine、SessionLocal 与 FastAPI 依赖 get_db。
"""

from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings


class Base(DeclarativeBase):
    """所有 SQLAlchemy 模型的基类；Alembic 的 target_metadata 取自这里。"""


engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, class_=Session)


def get_db() -> Iterator[Session]:
    """FastAPI 依赖：请求级 Session，请求结束即关闭。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
