"""FastAPI 应用装配（#1）。

本阶段只装两件事：应用实例 + CORS。
路由（auth / posts / rooms / bills / settlement）随 #2 起的各 Issue 逐个接入，
不在 #1 里先挂空路由占位。
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings

# 契约 §5 用到的动词只有 GET / POST / DELETE，外加浏览器预检的 OPTIONS。
# C4 只点名禁了 allow_origins 的通配，这里把方法与头也写明确，省得留通配的尾巴。
_ALLOWED_METHODS = ["GET", "POST", "DELETE", "OPTIONS"]
_ALLOWED_HEADERS = ["Authorization", "Content-Type"]


def create_app() -> FastAPI:
    app = FastAPI(title="SplitWay API", version="0.1.0")

    # 白名单来自 CORS_ORIGINS；config.py 已拒绝 "*"，此处不再兜底
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_credentials=True,
        allow_methods=_ALLOWED_METHODS,
        allow_headers=_ALLOWED_HEADERS,
    )

    return app


app = create_app()
