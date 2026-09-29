# SplitWay · 分途

> **面向小群体出行的同行撮合与共同账目结算工具**
> （Companion Matching & Shared Expense Settlement for Small Group Travel）
> 个人全栈项目 · V1 开发中 · 公开仓库

---

## 一句话定位

出行前，人要凑齐；出行中，钱要算清楚。SplitWay 把这两件事串成一条链：

```
发布搭子帖 → 建房间 → 房主审批成员 → 房间内记账 → 结算出每人应付/应收
```

它不是"一个旅游社区"。它是一条**可被自动化验证的多人协作账目链路**：多用户、有状态流转、有金额精度要求。

**V1 的目标不是功能多，是每一步都能被检验。**

- 产品需求：`docs/PRD.md`
- 系统架构与接口契约：`docs/architecture.md`
- 决策记录：`docs/decisions.md`
- 上手指南与协作规范：`docs/development-handbook.md`

---

## 这条链路回答什么

| # | 问题 | V1 能力 |
|---|---|---|
| 1 | 人能不能凑齐 | 发帖 / 浏览 / 申请加入 / 房主审批，成员四态流转（pending / joined / rejected / left） |
| 2 | 钱能不能算清 | 账单按参与人均分，金额全程整数分，分摊之和恒等于账单金额 |
| 3 | 结算能不能重复点 | 结算幂等：同一房间只产生一份结算结果，重复触发返回既有结果 |
| 4 | 别人能不能动我的账 | 越权返回 403，且有可重放的自动化断言 |

---

## 差异化在哪

1. **金额不碰浮点** —— 从数据库到 API 到前端状态，全程整数分（`BIGINT` / `int`）。换算只发生在前端输入框那一次。这不是洁癖：只要有一条路径用了 float，"三个人的钱加起来不等于总数"就只是时间问题。
2. **身份只信服务端** —— 任何接口都不接受 `userId` / `role` 之类的身份入参，操作者一律由服务端从 Token 解析。路径里出现的是**资源标识**（`member_id` / `post_id`），与身份彻底分开。
3. **环境一条命令起** —— `cp .env.example .env && docker compose up -d`。零硬编码凭据：JWT 密钥、数据库口令全部来自环境变量，缺失即启动失败，不提供"缺了就用默认值"的兜底。
4. **验收是命令，不是形容** —— 每条需求对应一条可执行命令或一个断言，见 `docs/PRD.md` 的 A / B / C 验收编号。
5. **不做清单是文档的一部分** —— 明确写出"不做什么"以及判定信号，见 `docs/PRD.md` §7 与 `docs/decisions.md`。

---

## 项目原则

1. **Honest Boundary** —— 写清能力边界与已知限制，不夸大。
2. **Evidence First** —— 所有结论附「命令 → 结果」，不写"应该没问题"。
3. **Fail Loudly** —— 配置缺失、状态非法、越权访问一律显式报错，不静默降级。
4. **Single Source of Truth** —— 决策进 `docs/decisions.md`，契约进 `docs/architecture.md`，代码不另立说法。
5. **范围冻结** —— V1 范围定完即冻结。加功能必须新开 Issue，不在既有 PR 里追加。

---

## 一条命令启动

```sh
cp .env.example .env && docker compose up -d
```

- 前端：http://localhost:8080 （nginx 托管 Vite 产物，`/api` 同源反代到后端）
- 后端 API 文档：http://localhost:8000/docs

本机前端开发：`cd frontend && npm install && npm run dev`（http://localhost:5173）

---

## 验证

```sh
# B1：后端测试
docker compose up -d db
docker compose run --rm backend pytest -q

# B2：两个账号走完整链路
BASE_URL=http://localhost:8000 python scripts/e2e_link.py

# C1：跨用户越权断言（全部 403，可重放）
BASE_URL=http://localhost:8000 python scripts/test_idor.py

# A2：硬编码凭据扫描
sh scripts/scan_secrets.sh
```

---

## 配置

所有配置来自环境变量，仓库只提交 `.env.example`（仅占位符）。

| 变量 | 说明 |
|---|---|
| `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` | 数据库账号与库名 |
| `DATABASE_URL` | 后端连接串（由 compose 组合，无需手工设置） |
| `JWT_SECRET` | JWT 签名密钥；**无默认值，缺失则后端启动失败** |
| `CORS_ORIGINS` | CORS 白名单，逗号分隔，**禁止 `*`** |
| `ROOM_MEMBER_LIMIT` | 房间人数上限（不含房主），默认 20 |

---

## 技术栈

| 层 | 技术 |
|---|---|
| 后端 | Python 3.13 · FastAPI · SQLAlchemy 2.0（同步）· Alembic |
| 数据库 | PostgreSQL 16（金额 `BIGINT` 整数分；部分唯一索引约束成员唯一性） |
| 认证 | JWT（HS256，密钥仅来自环境变量）· bcrypt |
| 前端 | Vue 3 · Vite · TypeScript · Tailwind CSS · Vue Router · axios |
| 前端服务 | 多阶段构建 → nginx 托管产物 + `/api` 同源反向代理 |
| 容器 | Docker Compose（db / backend / frontend） |
| 测试 | pytest · FastAPI TestClient · 独立测试库 |
| CI | GitHub Actions |

---

## 项目结构

```
├── docs/         设计 / 契约 / 决策 / 上手指南（一切决策先进 docs）
├── backend/      FastAPI 应用：认证 / 搭子帖 / 房间与成员 / 账单 / 结算
├── frontend/     Vue 3 应用 + 容器化配置
├── scripts/      可重放的验收脚本（端到端链路 / 越权断言 / 凭据扫描）
└── .github/      CI 工作流
```

---

## 团队与分工

| 角色 | 成员 | GitHub | 负责范围 |
|---|---|---|---|
| **Project Lead & Architect (Owner)** | 肖宇翔 | `@YUXIANG-XIAO123` | 架构与接口契约、Issue 派发与放行、PR 合并、验收签字 |
| **Backend Engineer** | 陈展鸿 | `@gasterfly` | Issue `#1`–`#6`：骨架与迁移 / 认证 / 搭子帖 / 房间与成员 / 账单与结算 / 后端测试 |
| **Frontend Engineer** | 包伟榕 | `@LunarQueen` | Issue `#7`–`#10`：骨架与登录 / 列表与详情 / 房间页 / 容器化 |
| **独立验收 · 红队审计** | 待定 | — | Issue `#11` / `#12` |

架构决策层为 **Owner**：架构与接口契约的草案可由 AI 辅助起草，**最终裁定与签字在 Owner**；任何内容合入 `main` 前须由人过一遍。AI 辅助开发的口径见 `docs/development-handbook.md` 附录 E。

详见 `docs/团队分工书.md`。

---

## 阶段计划

V1 分三个阶段推进。**同一时间只开当前阶段的 Issue**，后续阶段先关闭留档，本阶段收口后由 Owner 重新打开并放行。

| 阶段 | 内容 | Issue | 收口标志 |
|---|---|---|---|
| **阶段1 · 立柱** | 环境能一条命令起；身份通 | `#1` `#2` `#7` | `cp .env.example .env && docker compose up -d` 三服务可用；浏览器能注册并登录；`pytest` 认证用例全绿 |
| **阶段2 · 主链路** | 找搭子 → 建房间 → 记账 → 结算，全链打通 | `#3` `#4` `#5` `#8` `#9` | 两个账号真实走完整条链路；前端全程可操作 |
| **阶段3 · 收口** | 测试证据 + 容器化 + 独立验收 + 红队审计 | `#6` `#10` `#11` `#12` | PRD 的 A / B / C 全部验收编号复跑通过 |

规则：

1. 阶段未开启的 Issue 处于**关闭**状态，不得提前开工。
2. Issue 必须带 `状态:已批准` 标签才能开工；`状态:待整改` 可直接改。
3. 当前阶段的收口标志未达成，不开启下一阶段。

---

## 生命周期与协作

```
Issue（Owner 派发）→ 设计(docs) → 契约冻结 → 实现(feature/PR) → 复审 → 验收 → 合并 main
```

- 分支：`main`（可运行、受保护）← `feature/<模块>-<简述>`、`fix/<模块>-<简述>`、`docs/<简述>`
- 禁止 `test`、`temp`、`w1` 这类随意命名
- Issue 带 `状态:已批准` 才能开工；`状态:待整改` 可直接改
- PR 正文自行撰写（仓库不设自动模板），格式见 `docs/development-handbook.md` 附录 B
- Issue 由 Owner 统一关闭，PR 不得自行合并

---

## 第一次贡献（从这里开始）

1. 读 `docs/development-handbook.md` —— 环境、分支、规范、PR 格式全在里面
2. 读 `docs/PRD.md` —— 明确 V1 范围与 A / B / C 验收编号
3. 读 `docs/architecture.md` —— 数据模型、状态机、**接口契约（§5）**、任务分解
4. 从带 `状态:已批准` 且未被人认领的 Issue 开工

---

## 自研边界与设计约束

本项目从功能边界到技术方案、数据模型、接口契约、算法全部独立完成，**代码 100% 自研**，不复制任何第三方代码、配置或数据库结构。

安全约束来自**该领域广为人知的常见缺陷**，逐条转成了硬约束并纳入 P0 验收：

| 常见缺陷 | 本项目约束 |
|---|---|
| 身份靠前端传参导致越权 | 身份只从服务端 Token 解析，接口不收身份入参 |
| JWT 密钥硬编码 | 密钥仅来自环境变量，缺失即启动失败 |
| 口令明文入库、配置文件未忽略 | 只提交 `.env.example`，`.env` 被忽略 |
| CORS 通配 `*` | 白名单走环境变量，永不使用 `*` |
| 上传目录裸奔、上传文件进版本库 | 不匿名可枚举；上传文件不入库（V1 不做上传） |
| 测试缺失 | 核心链路 + 越权均有自动化用例 |

完整说明见 `docs/来源说明.md`。
