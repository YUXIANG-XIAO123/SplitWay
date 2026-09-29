"""应用配置：全部来自环境变量（#1）。

三条规则，对应 #1 交付物与团队分工书硬约束 3：

1. 本模块**只读 ``os.environ``**，不加载 .env 文件。
   .env 由 docker compose 注入为容器环境变量；代码侧再读一次 .env，
   等于引入第二套配置来源。
2. 必填项缺失或为空 → **导入本模块即抛 ConfigError**，错误信息打印出缺失的变量名。
   不提供"缺了就退回默认值"的兜底，避免带着半套配置跑起来。
3. 只有文档明确规定有默认值的项才给默认值（见 ``_DEFAULTS``），其余一律必填。
"""

from __future__ import annotations

import os
from dataclasses import dataclass

# 必填：缺失或为空即启动失败
_REQUIRED_NAMES: tuple[str, ...] = ("DATABASE_URL", "JWT_SECRET", "CORS_ORIGINS")

# 文档明确规定有默认值的项；出处写在注释里，其余一律不给默认值
_DEFAULTS: dict[str, str] = {
    # 房间人数上限默认 20：decisions.md D11、README 配置表
    "ROOM_MEMBER_LIMIT": "20",
}

# JWT 密钥最小长度：development-handbook.md §2 ——「JWT_SECRET 至少要 32 字符」
_JWT_SECRET_MIN_LENGTH = 32


class ConfigError(RuntimeError):
    """配置缺失或不合法。在导入本模块时抛出，不做运行期兜底。"""


@dataclass(frozen=True)
class Settings:
    database_url: str
    jwt_secret: str
    cors_origins: tuple[str, ...]
    room_member_limit: int


def _get(name: str) -> str:
    """取环境变量并去掉首尾空白；未设置或全空白一律视为缺失。"""
    raw = os.environ.get(name)
    if raw is None:
        return ""
    return raw.strip()


def _load() -> Settings:
    missing = [name for name in _REQUIRED_NAMES if not _get(name)]
    if missing:
        raise ConfigError(
            "缺少必需的环境变量：" + "、".join(missing)
            + "。请先 cp .env.example .env 并填入真实值；本服务不提供默认值，缺失即拒绝启动。"
        )

    jwt_secret = _get("JWT_SECRET")
    if len(jwt_secret) < _JWT_SECRET_MIN_LENGTH:
        raise ConfigError(
            f"环境变量 JWT_SECRET 长度不足：当前 {len(jwt_secret)} 字符，"
            f"要求至少 {_JWT_SECRET_MIN_LENGTH} 字符。"
        )

    cors_origins = tuple(
        origin.strip() for origin in _get("CORS_ORIGINS").split(",") if origin.strip()
    )
    if not cors_origins:
        raise ConfigError("环境变量 CORS_ORIGINS 解析后为空，请至少给出一个来源。")
    if "*" in cors_origins:
        raise ConfigError(
            '环境变量 CORS_ORIGINS 不允许使用 "*"（团队分工书 硬约束 4）：请改为具体来源，逗号分隔。'
        )

    limit_raw = _get("ROOM_MEMBER_LIMIT") or _DEFAULTS["ROOM_MEMBER_LIMIT"]
    try:
        room_member_limit = int(limit_raw)
    except ValueError as exc:
        raise ConfigError(
            f"环境变量 ROOM_MEMBER_LIMIT 必须是整数，当前值为 {limit_raw!r}。"
        ) from exc
    if room_member_limit < 1:
        raise ConfigError(
            f"环境变量 ROOM_MEMBER_LIMIT 必须 >= 1，当前值为 {room_member_limit}。"
        )

    return Settings(
        database_url=_get("DATABASE_URL"),
        jwt_secret=jwt_secret,
        cors_origins=cors_origins,
        room_member_limit=room_member_limit,
    )


# 模块级单例：导入即校验，配置不全的进程根本起不来。
settings = _load()
