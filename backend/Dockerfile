# SplitWay 后端镜像（#1）
# 依据：architecture.md §1 技术选型——Python 3.13，容器用 python:3.13-slim。
FROM python:3.13-slim

# 不写 .pyc、日志不缓冲：启动失败时 docker logs 能按行直接看到原因
# PYTHONUTF8=1：把 locale 编码固定为 UTF-8。仓库内注释是中文，
# 若镜像 locale 未设置（LANG 为空），configparser 之类按 locale 解码的读取会失败。
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONUTF8=1

WORKDIR /app

# 依赖层与代码层分开：只改代码时不会让依赖重新安装
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# 建库走 Alembic：容器启动先把迁移推到 head，再起应用。
# 迁移失败则容器立即退出，不会带着旧 schema 硬起（Fail Loudly）。
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port 8000"]
