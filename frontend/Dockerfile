# SplitWay 前端镜像：多阶段构建
# 阶段 1：Node 构建 Vite 产物；阶段 2：nginx 托管静态文件并反代 /api。
# 约定（见 docker-compose.yml 的 frontend 服务）：构建上下文 ./frontend，容器监听 80。

# ---------- 阶段 1：构建 ----------
FROM node:22-alpine AS build

WORKDIR /app

# 先装依赖，利用 Docker 层缓存。
#
# 历史与为何改回 npm ci（2026-10-12）：
#   此处原先用 `npm install` 而非 `npm ci`，理由写的是"容器内为全新文件系统，npm install 会按
#   容器平台重新解析并补齐 optional 依赖"。**该假设不成立**——只要 package-lock.json 被 COPY 进来，
#   容器里的 npm install 就跟着 lock 走；而旧 lock 缺失 rollup / esbuild 的平台二进制条目
#   （optionalDependencies），于是前端镜像必然构建失败（MODULE_NOT_FOUND: rollup/dist/native.js）。
#   已在干净容器中重生成完整 lockfile（204 条，其中 51 条平台条目，覆盖 linux/win32/darwin 等），
#   故改回 `npm ci`：锁定版本、可复现，且 lock 不完整时会在安装阶段就明确报错而不是留到构建阶段。
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund

# 再复制源码构建
COPY . .
RUN npm run build

# ---------- 阶段 2：运行 ----------
FROM nginx:1.27-alpine AS runtime

# 自定义 nginx 配置：静态托管 + /api 反向代理到 backend:8000
COPY nginx.conf /etc/nginx/conf.d/default.conf

# 拷贝构建产物
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

# 健康检查：发一次真实 HTTP 请求验证 nginx 确实在提供页面。
# nginx:1.27-alpine 自带 busybox wget，无需额外安装（与 backend 用标准库的做法同思路）。
#
# 为什么必须有：PRD 的 A1 验收判据是「三个容器均 healthy」。此前只有 db 与 backend 有 healthcheck，
# frontend 没有 —— 也就是说 A1 的判据**根本无法达成**，docker compose ps 里 frontend 永远只显示 Up。
HEALTHCHECK --interval=5s --timeout=3s --start-period=5s --retries=12 \
  CMD wget -q -O /dev/null http://127.0.0.1/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
