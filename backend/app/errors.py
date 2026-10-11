"""统一业务错误。

错误响应体统一为 ``{"detail": {"code": "<字符串码>", "message": "<中文说明>"}}``，
与 architecture.md §5.1 冻结契约一致，不额外包裹 Result 层。
"""

from __future__ import annotations

from fastapi import HTTPException, status


def error(status_code: int, code: str, message: str) -> HTTPException:
    """构造一个符合契约的业务异常。

    Args:
        status_code: HTTP 状态码。
        code: 机器可读的错误码。
        message: 面向使用者的中文说明。

    Returns:
        可直接 raise 的 HTTPException。
    """
    return HTTPException(status_code=status_code, detail={"code": code, "message": message})


def unauthorized(message: str = "未认证或登录状态已失效。") -> HTTPException:
    """401：未认证（C5）。"""
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"code": "unauthorized", "message": message},
        headers={"WWW-Authenticate": "Bearer"},
    )


def forbidden(message: str = "无权访问该资源。") -> HTTPException:
    """403：已认证但无权限（C1 / B4 / B6）。"""
    return error(status.HTTP_403_FORBIDDEN, "forbidden", message)


def not_found(message: str = "资源不存在。") -> HTTPException:
    """404：资源不存在。"""
    return error(status.HTTP_404_NOT_FOUND, "not_found", message)


def conflict(message: str = "操作与当前状态冲突。") -> HTTPException:
    """409：状态冲突（B5 等）。"""
    return error(status.HTTP_409_CONFLICT, "conflict", message)


def bad_request(message: str = "请求参数不合法。") -> HTTPException:
    """400：请求不合法。"""
    return error(status.HTTP_400_BAD_REQUEST, "bad_request", message)
