"""密码哈希与 JWT 签发/校验。

约束：
- 直接使用 ``bcrypt`` 库，**不使用 passlib**（D6）。
- JWT 密钥只从环境变量读取（``settings.jwt_secret``），无默认值（C3）。
- 任何日志/异常都不得回显密码、token、密钥。
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.config import settings

# bcrypt 只处理前 72 字节，超长输入需要显式截断以避免抛错。
_BCRYPT_MAX_BYTES = 72


def _to_bcrypt_bytes(password: str) -> bytes:
    """把明文密码编码并截断到 bcrypt 可处理的长度。"""
    return password.encode("utf-8")[:_BCRYPT_MAX_BYTES]


def hash_password(password: str) -> str:
    """对明文密码做 bcrypt 哈希。

    Args:
        password: 明文密码。

    Returns:
        形如 ``$2b$...`` 的哈希字符串。
    """
    hashed = bcrypt.hashpw(_to_bcrypt_bytes(password), bcrypt.gensalt())
    return hashed.decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """校验明文密码与哈希是否匹配。

    Args:
        password: 明文密码。
        password_hash: 数据库中存储的哈希。

    Returns:
        匹配返回 True，否则 False（不抛出，避免泄露细节）。
    """
    try:
        return bcrypt.checkpw(_to_bcrypt_bytes(password), password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def create_access_token(user_id: int) -> str:
    """签发 HS256 的访问令牌。

    Args:
        user_id: 用户主键，写入 ``sub`` 声明。

    Returns:
        编码后的 JWT 字符串。
    """
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> int:
    """解析访问令牌并返回其中的用户主键。

    Args:
        token: JWT 字符串。

    Returns:
        ``sub`` 声明对应的整数用户 ID。

    Raises:
        jwt.PyJWTError: 令牌无效、过期或签名不匹配。
    """
    payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    subject = payload.get("sub")
    if subject is None:
        raise jwt.InvalidTokenError("token 缺少 sub 声明")
    return int(subject)
