"""FastAPI 应用装配。

- CORS 白名单走环境变量（C4），永不为 '*'。
- 统一注册路由到 /api 前缀。
- 提供 /api/health 供容器健康检查。
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import auth, bills, posts, rooms, settlement

app = FastAPI(title="SplitWay API", version="1.0.0")

# CORS：只允许白名单来源，且允许携带凭据；绝不使用通配符。
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(posts.router, prefix="/api/posts", tags=["posts"])
app.include_router(rooms.router, prefix="/api/rooms", tags=["rooms"])
app.include_router(bills.router, prefix="/api/rooms", tags=["bills"])
app.include_router(settlement.router, prefix="/api/rooms", tags=["settlement"])


@app.get("/api/health", tags=["health"])
def health() -> dict[str, str]:
    """健康检查端点，供 docker healthcheck 使用。"""
    return {"status": "ok"}
