"""应用配置。

全部配置项只从环境变量读取，缺失关键项时启动直接失败（不提供任何默认密钥）。
这是安全基线 C3 / A3 的兑现点：仓库与镜像中不存在明文凭据与默认密钥。
"""

from __future__ import annotations

import os

# 关键项：缺失即启动失败，绝不允许回退到默认值。
_REQUIRED_ENV_VARS = ("DATABASE_URL", "JWT_SECRET")


def _require(name: str) -> str:
    """读取必填环境变量，缺失或为空时抛出 RuntimeError 使进程启动失败。

    Args:
        name: 环境变量名。

    Returns:
        环境变量值（非空字符串）。

    Raises:
        RuntimeError: 环境变量缺失或为空字符串。
    """
    value = os.environ.get(name)
    if value is None or value.strip() == "":
        raise RuntimeError(
            f"缺少必需的环境变量 {name!r}：启动被拒绝。"
            f"请在 .env 中配置后重试（参考 .env.example）。"
        )
    return value


def _optional(name: str, default: str) -> str:
    """读取可选环境变量，未设置时返回默认值。"""
    value = os.environ.get(name)
    if value is None or value.strip() == "":
        return default
    return value


def _split_origins(raw: str) -> list[str]:
    """把逗号分隔的 CORS 白名单解析为列表，并对通配符做硬性拒绝。"""
    origins = [item.strip() for item in raw.split(",") if item.strip()]
    if not origins:
        raise RuntimeError("CORS_ORIGINS 不能为空。")
    if "*" in origins:
        raise RuntimeError(
            "CORS_ORIGINS 不允许包含通配符 '*'：安全基线 C4 要求白名单。"
        )
    return origins


class Settings:
    """运行期配置对象（不可变语义：仅在启动时构造一次）。"""

    def __init__(self) -> None:
        """从环境变量装载全部配置，并在缺失关键项时抛出异常。"""
        # 数据库连接串（驱动固定 psycopg 3）。
        self.database_url: str = _require("DATABASE_URL")

        # JWT：密钥必须外置，无默认值。
        self.jwt_secret: str = _require("JWT_SECRET")
        self.jwt_algorithm: str = _optional("JWT_ALGORITHM", "HS256")
        self.jwt_expire_minutes: int = int(_optional("JWT_EXPIRE_MINUTES", "720"))

        # CORS 白名单：默认只放行本机 Vite 开发端口，永不为 '*'。
        self.cors_origins: list[str] = _split_origins(
            _optional("CORS_ORIGINS", "http://localhost:5173")
        )

        # 房间人数上限（不含房主）。
        self.room_member_limit: int = int(_optional("ROOM_MEMBER_LIMIT", "20"))

        # 便于自检：确保必填项确实存在（防御性再校验一次）。
        for name in _REQUIRED_ENV_VARS:
            if not os.environ.get(name):
                raise RuntimeError(f"缺少必需的环境变量 {name!r}：启动被拒绝。")


# 模块级单例：导入即构造，缺关键项则进程在启动阶段直接失败。
settings = Settings()
