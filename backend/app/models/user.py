"""users 表模型（#1 只建这一张表；其余表随对应 Issue 逐个加迁移）。

字段与约束依据 docs/architecture.md §3.2：id / username / password_hash / created_at，
username 唯一，且只存哈希。
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Identity, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
