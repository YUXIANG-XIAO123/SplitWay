"""认证相关出入参。"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class RegisterRequest(BaseModel):
    """注册入参。"""

    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=6, max_length=128)


class LoginRequest(BaseModel):
    """登录入参。"""

    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1, max_length=128)


class UserOut(BaseModel):
    """用户公开信息。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str


class TokenResponse(BaseModel):
    """登录成功返回。"""

    access_token: str
    token_type: str = "bearer"
    user: UserOut
