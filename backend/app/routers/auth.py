"""认证路由：register / login / me。"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.errors import conflict, unauthorized
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserOut
from app.security import create_access_token, hash_password, verify_password

router = APIRouter()


@router.post("/register", status_code=201, response_model=UserOut)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> User:
    """注册新用户。用户名冲突返回 409。"""
    existing = db.execute(
        select(User).where(User.username == payload.username)
    ).scalar_one_or_none()
    if existing is not None:
        raise conflict("用户名已被占用。")

    user = User(username=payload.username, password_hash=hash_password(payload.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    """登录并签发 JWT。凭据错误统一返回 401。"""
    user = db.execute(
        select(User).where(User.username == payload.username)
    ).scalar_one_or_none()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise unauthorized("用户名或密码错误。")

    token = create_access_token(user.id)
    return TokenResponse(access_token=token, user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)) -> User:
    """返回当前登录用户信息。"""
    return current_user
