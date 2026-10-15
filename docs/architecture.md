# SplitWay 系统架构与接口契约（V1）

| 项 | 内容 |
|---|---|
| 文档版本 | V1.0（架构与接口契约裁定：Owner） |
| 上游依据 | `docs/PRD.md`（V1.0） |
| 冻结状态 | 选型已冻结；契约已冻结（Owner 可推翻任意一条，工程师按修改返工） |
| 语言 | 中文 |

---

## 1. 技术选型（已冻结）

| 层 | 选定 | 备注 |
|---|---|---|
| 后端语言 | Python 3.13 | Owner 已定方向（Python）；版本对齐本机实测环境（3.13），容器用 `python:3.13-slim` |
| 后端框架 | FastAPI | 自带 OpenAPI（服务 C2 验收）；依赖注入便于统一"身份只来自服务端" |
| 执行模型 | **同步**（`def` 端点 + SQLAlchemy 同步 Session） | V1 并发量极低；同步实现的事务边界与堆栈可读性优于 async。FastAPI 会把 `def` 端点放进线程池 |
| ORM | SQLAlchemy 2.0（`Mapped[]` 声明式） | 与 Alembic 同源 |
| 迁移 | Alembic | 解决"建库脚本不可重入"的问题：`DROP TABLE IF EXISTS` 式的脚本无法重复执行 |
| 数据库 | PostgreSQL 16 | 金额 `BIGINT`；部分唯一索引用于成员唯一性 |
| 数据库驱动 | psycopg 3 | 同步驱动 |
| 认证 | JWT（HS256，PyJWT） | 密钥仅来自环境变量 |
| 密码哈希 | `bcrypt` 库（**不用 passlib**） | passlib 1.7.4 与 bcrypt 4.x 存在已知不兼容，直接调用 bcrypt 避免该依赖陷阱 |
| 前端 | Vue 3 + Vite + TypeScript + Tailwind CSS | Owner 已拍（见 §7 D2） |
| 前端路由 | Vue Router | 4 个页面 |
| 前端状态 | 不引入 Pinia，用 composable（`useAuth`） | 状态只有"当前用户 + token" |
| 前端请求 | axios + 响应拦截器 | 统一处理 401 跳登录 |
| 容器 | docker compose：`db` / `backend` / `frontend` | V1 P0-1 的兑现方式 |
| 测试 | pytest + FastAPI TestClient + 独立测试库 | 越权与精度断言必须可重放 |

### 1.1 前端服务的形态（影响 C4）

`frontend` 容器 = **多阶段构建 → nginx 托管 Vite 产物**，并由 nginx 把 `/api` 反向代理到 `backend`。

| 收益 | 说明 |
|---|---|
| 浏览器与后端**同源** | 正常路径下根本不触发 CORS，从结构上消灭"通配 CORS"这一类问题 |
| C4 仍然成立 | 后端 CORS 白名单走环境变量 `CORS_ORIGINS`，默认只放行 `http://localhost:5173`（供本机 `npm run dev` 调试），**永不使用 `*`** |
| 本地开发不受影响 | 日常开发用 `npm run dev`（5173），改代码即时生效 |

---

## 2. 目录结构

```
SplitWay/
├── .env.example                ← 只提交占位符，.env 被忽略
├── .gitignore
├── docker-compose.yml
├── README.md
├── docs/
│   ├── PRD.md
│   ├── architecture.md         ← 本文档
│   ├── decisions.md            ← 决策记录（每条一行）
│   └── 来源说明.md              ← 自研边界与设计约束说明
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── alembic.ini
│   ├── alembic/versions/
│   ├── app/
│   │   ├── main.py             ← FastAPI 应用装配、CORS、路由注册
│   │   ├── config.py           ← 全部配置从环境变量读，缺失即启动失败
│   │   ├── db.py               ← engine / SessionLocal / get_db
│   │   ├── models/             ← SQLAlchemy 模型
│   │   ├── schemas/            ← Pydantic 出入参
│   │   ├── deps.py             ← get_current_user / require_room_member / require_room_host
│   │   ├── routers/            ← auth / posts / rooms / bills / settlement
│   │   └── services/
│   │       ├── split.py        ← 均分 + 最大余额法
│   │       └── settlement.py   ← 净额计算（纯整数加减）
│   └── tests/
│       ├── conftest.py
│       ├── test_auth.py
│       ├── test_posts.py
│       ├── test_rooms.py
│       ├── test_bills.py
│       ├── test_settlement.py
│       ├── test_split_precision.py   ← B3
│       └── test_idor.py              ← C1
├── frontend/
│   ├── Dockerfile              ← 多阶段：node 构建 → nginx 托管
│   ├── nginx.conf              ← 静态托管 + /api 反代
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   └── src/
│       ├── main.ts
│       ├── App.vue
│       ├── router/index.ts
│       ├── api/                ← axios 实例 + 各模块接口
│       ├── composables/useAuth.ts
│       └── views/              ← Login / PostList / PostDetail / Room
└── scripts/
    ├── e2e_link.py             ← B2：U1/U2 走完整链路
    ├── test_idor.py            ← C1：越权断言
    └── scan_secrets.sh         ← A2：凭据扫描
```

---

## 3. 数据模型

### 3.1 金额表示（硬约定）

> **全系统金额一律用整数分（`BIGINT`），从数据库到 API 到前端状态，不出现浮点数。**

| 位置 | 表示 |
|---|---|
| 数据库 | `amount_cents BIGINT NOT NULL CHECK (amount_cents > 0)` |
| API 入参 / 出参 | `amount_cents: int` |
| 前端 | 输入元（两位小数）→ 立即乘 100 取整 → 全程用分；展示时除 100 格式化 |

这样做的原因：B3 要求"3 人均分 100.00 求和仍等于 100.00"。只要换算点唯一（前端输入处），后续全是整数，浮点误差在结构上不可能出现。

### 3.2 表结构

| 表 | 关键字段 | 约束 / 说明 |
|---|---|---|
| `users` | `id`, `username`, `password_hash`, `created_at` | `username` 唯一；只存哈希 |
| `partner_posts` | `id`, `owner_id`→users, `destination`, `depart_date`, `need_count`, `note`, `status`, `created_at` | `status` ∈ {open, closed}；`need_count` ≥ 2 |
| `rooms` | `id`, `post_id`→partner_posts, `owner_id`→users, `status`, `member_limit`, `created_at` | `status` ∈ {open, settled}；`member_limit` 默认 20（配置可改） |
| `room_members` | `id`, `room_id`→rooms, `user_id`→users, `status`, `role`, `created_at`, `updated_at` | `status` ∈ {pending, joined, rejected, left}；`role` ∈ {owner, member} |
| `bills` | `id`, `room_id`→rooms, `payer_id`→**users**, `amount_cents`, `note`, `created_at` | `amount_cents > 0` |
| `bill_shares` | `id`, `bill_id`→bills, `user_id`→**users**, `amount_cents` | 分摊明细；**同一账单的分摊额之和必须等于账单金额** |
| `settlements` | `id`, `room_id`→rooms **唯一**, `created_at` | 唯一约束即幂等保证（B5） |
| `settlement_items` | `id`, `settlement_id`→settlements, `user_id`→**users**, `paid_cents`, `share_cents`, `net_cents` | 每人一行 |

> **账务落库一律用 `user_id`**（`bills.payer_id` / `bill_shares.user_id` / `settlement_items.user_id` 全部外键到 `users`）。
> 原因见 §5.5 与 `docs/decisions.md` 的 D20：账目主体是"人"，要跨成员状态变化存活；结算数学也是按用户汇总的。
> `room_members.id` 只用于**房间内的成员资格校验**，不落进账务表。

**关键约束（PostgreSQL 部分唯一索引）**：

```sql
-- 同一房间内，同一用户的"有效成员记录"只能有一条
-- 有效 = pending 或 joined；rejected / left 属历史记录，可再次申请
CREATE UNIQUE INDEX uq_room_member_active
  ON room_members (room_id, user_id)
  WHERE status IN ('pending', 'joined');
```

这条索引在数据库层兜底"重复申请 / 重复加入"，不依赖应用层判断——应用层判断在并发下不可靠。

---

## 4. 状态机与业务规则

### 4.1 成员状态机（V1 固定四态）

```
        ┌──────────── 房主通过 ───────────► joined ── 本人退出 ──► left(终态)
申请 ──► pending ── 房主拒绝 ──► rejected(终态)
        └──────────── 本人撤回 ─────────► left(终态)
```

| 规则 | 内容 |
|---|---|
| 房主 | 创建房间时自动写入一条 `role=owner, status=joined` 记录，不占 `member_limit` 名额 |
| 申请 | 仅"非该房间成员"可申请；已有 pending/joined 记录时调用返回 **409** |
| 审批 | 仅房主可调用；`joined` 人数已达 `member_limit` 时返回 **409** |
| 退出 | 仅本人可退出；`status=joined` → `left`；房主不可退出（V1） |
| 记账资格 | 仅 `status=joined` 的成员可记账、可被选为分摊人、可被选为付款人；否则 **403** |

### 4.2 分摊规则（V1 只做均分）

> **V1 不支持不等额分摊**（不等额列入 P1 留档）。这砍掉了一整类边界问题。

均分 + 最大余额法：

```
n = 参与分摊成员数
base = amount_cents // n
r    = amount_cents % n
按 userId 升序，前 r 名成员各多分 1 分，其余分 base
```

必要的说明：**在"均分"场景下所有成员的"小数部分"完全相同，最大余额法退化为"按 userId 升序分配余数"**。规则仍然是确定性的、可断言的；最大余额法真正的价值要等引入不等额分摊后才体现。

不变式（必须有断言）：`sum(bill_shares.amount_cents) == bills.amount_cents`

### 4.3 结算规则

```
paid_cents[user]  = 该用户作为 payer 的账单金额之和
share_cents[user] = 该用户在所有 bill_shares 中的分摊额之和
net_cents[user]   = paid_cents[user] - share_cents[user]
                    net > 0 → 应收（别人欠他）；net < 0 → 应付
```

- 结算阶段是**纯整数加减**，不产生任何余数。余数只产生在 4.2 的分摊环节。
- **幂等（B5）**：`settlements.room_id` 唯一。已结算的房间再次触发，直接返回已存在的结算结果，不新建记录。
- **结算后只读（Q6 裁定）**：`rooms.status = settled` 后，该房间的账单不可新增、不可删除（返回 **409**）。

---

## 5. 接口契约（已冻结）

统一前缀 `/api`。身份**只**来自 `Authorization: Bearer <token>`，服务端解析。

### 5.1 路径设计约定

| 约定 | 说明 |
|---|---|
| 路径中**不出现** `user_id` | 涉及"被操作的成员"时一律用 `member_id`（`room_members.id`），从命名上与"操作者身份"彻底区分开 |
| 操作者身份 | 一律由 `get_current_user` 从 token 解析，**任何接口都不接受身份入参** |
| 校验失败 | 由 FastAPI / Pydantic 自动返回 422 |
| 业务错误 | 统一 `{"detail": {"code": "<字符串码>", "message": "<中文说明>"}}`，不自定义 Result 包装层 |

> **对 C2 验收口径的澄清**：C2 要禁的是"**操作者身份**作为入参"。`{member_id}` / `{post_id}` 这类**资源标识**作为路径参数是正常的 REST 设计，不属于身份入参。独立验收时按此口径判定。

### 5.2 认证

| 方法 | 路径 | 入参 | 出参 | 权限 |
|---|---|---|---|---|
| POST | `/api/auth/register` | `{username, password}` | 201 `{id, username}` | 匿名 |
| POST | `/api/auth/login` | `{username, password}` | 200 `{access_token, token_type:"bearer", user:{id, username}}` | 匿名 |
| GET | `/api/auth/me` | — | 200 `{id, username}` | 已登录 |

### 5.3 搭子帖

| 方法 | 路径 | 入参 | 出参 | 权限 |
|---|---|---|---|---|
| POST | `/api/posts` | `{destination, depart_date, need_count, note?}` | 201 帖子 | 已登录 |
| GET | `/api/posts` | `?status=open&page=1&size=20` | 200 `{items[], total}` | 已登录 |
| GET | `/api/posts/{post_id}` | — | 200 帖子 + 申请人列表（仅帖主可见申请人明细）+ **`room_id`（该帖已创建的房间 id，未创建为 `null`）** | 已登录 |
| DELETE | `/api/posts/{post_id}` | — | 204 | **仅帖主**，否则 403；见下方房间处理规则 |

**删帖时的房间处理（三档）** —— 帖子的房间由 `#1` 时的"有房间就一律拒绝"放宽为：

| 情况 | 行为 |
|---|---|
| 无房间 | 直接删帖 |
| 有房间，且**房间为空**（0 账单、未结算） | 连同空房间一起删（`room_members` 由 `Room.members` 级联清除）→ 204 |
| 有房间，且**有账单或已结算** | **409**「该帖子的房间已有账单或已结算，无法删除帖子。」—— 保护账目 |

放宽的理由：原规则把"建错房间想重来"也堵死了 —— `create_room` 对同一帖子返回 409（一条帖子只能有一个房间），
于是用户既删不掉帖子、也建不了新房间，**没有任何出路**。空房间不承载账目，删掉是安全的。

> 实现注意：`rooms.post_id → partner_posts.id`，删房间与删帖子**不能放在同一次 flush**
> （SQLAlchemy 不保证先删子表，会撞 `rooms_post_id_fkey`）。代码里在 `db.delete(room)` 后显式 `db.flush()`。

### 5.4 房间与成员

| 方法 | 路径 | 入参 | 出参 | 权限 |
|---|---|---|---|---|
| POST | `/api/rooms` | `{post_id}` | 201 房间 | **仅帖主**；创建者自动成为房主 |
| GET | `/api/rooms` | — | 200 我参与的房间列表 | 已登录 |
| GET | `/api/rooms/{room_id}` | — | 200 房间详情 | **仅该房间 joined/owner 成员**，否则 403（C1） |
| GET | `/api/rooms/{room_id}/members` | — | 200 成员列表 | 同上 |
| POST | `/api/rooms/{room_id}/join-requests` | — | 201 成员记录(pending) | 本人；重复申请 409 |
| POST | `/api/rooms/{room_id}/members/{member_id}/approve` | — | 200 | **仅房主**，否则 403（B6） |
| POST | `/api/rooms/{room_id}/members/{member_id}/reject` | — | 200 | **仅房主**，否则 403 |
| POST | `/api/rooms/{room_id}/leave` | — | 200 | 仅本人（member_id 隐含为操作者自身） |

### 5.5 账单

| 方法 | 路径 | 入参 | 出参 | 权限 |
|---|---|---|---|---|
| POST | `/api/rooms/{room_id}/bills` | `{payer_id?, amount_cents, note?, participant_member_ids[]}` | 201 账单 + 分摊明细 | **仅 joined 成员**；房间已结算 → 409（B4/B5） |
| GET | `/api/rooms/{room_id}/bills` | — | 200 账单列表（含分摊） | **仅 joined/owner 成员** |
| DELETE | `/api/rooms/{room_id}/bills/{bill_id}` | — | 204 | **仅房主**；房间已结算 → 409 |

**提交体里有两个标识字段，分属两个 ID 空间，各自有明确理由**（见 D20）：

| 字段 | ID 空间 | 为什么是这个空间 |
|---|---|---|
| `participant_member_ids` | **房间成员 ID**（`room_members.id`） | 入口要校验"是不是该房间的 joined 成员"，`member_id` 是天然键；校验通过后转 `user_id` 落库 |
| `payer_id` | **用户 ID**（`users.id`） | 付款人是"人"，要跨成员状态变化（退出 / 重进 / 换房间）存活；结算数学按用户汇总，落库统一为 `user_id` |

- `payer_id` 省略时默认为操作者本人；指定时，该用户必须是该房间的 joined 成员。
- `participant_member_ids` 必须全部是该房间的 joined 成员，且非空。
- 若 `payer_id` 对应的用户不在 `participant_member_ids` 中，属合法（代付场景）。
- 出参 `payer_id` 与 `shares[].user_id` 同为**用户 ID**。

### 5.6 结算

| 方法 | 路径 | 入参 | 出参 | 权限 |
|---|---|---|---|---|
| POST | `/api/rooms/{room_id}/settlement` | — | 200 结算结果 | **仅房主**，否则 403；**房间无账单 → 409**；已结算 → 200（幂等） |
| GET | `/api/rooms/{room_id}/settlement` | — | 200 结算结果 / 404 未结算 | 仅 joined/owner 成员 |

**前置条件：POST 结算要求房间至少有一条账单。** 零账单结算会产生一份"全员净额 0"的无意义结果，
同时把房间置为 `settled` 只读；而 `create_room` 对同一帖子返回 409（一条帖子只能有一个房间），
**一旦误结算这条路就彻底堵死**。因此后端直接拦截，前端也在无账单时禁用按钮并给出提示。

结算结果出参：

  ```json
  {
    "room_id": 1,
    "settled_at": "2026-09-28T15:00:00Z",
    "items": [
      {"user_id": 1, "username": "u1",
       "paid_cents": 10000, "share_cents": 3334, "net_cents": 6666}
    ],
    "total_cents": 10000,
    "check": {"sum_share_equals_total": true}
  }
  ```

  **`items` 只以 `user_id` 标识主体，不含 `member_id`。** 结算是账务快照，财务主体是"人"而非"房间成员记录"；
  `member_id` 只在记账入参（`participant_member_ids`）里作为"房间内成员资格"的入口存在。
  早先出参里带过一个 `member_id`，但它是读取时按**当前**成员记录反查的（取 id 最大的那条），
  并非结算时固化的值 —— 一旦成员记录变化就会漂移，属于会误导的展示字段，已移除。

`check.sum_share_equals_total` 是给验收脚本直接读的不变式字段——把 B3 的断言变成读一个布尔值。

### 5.7 错误码语义（全系统统一）

| 状态码 | 语义 | 典型场景 |
|---|---|---|
| 401 | 未认证 | 无 token / token 无效或过期（C5） |
| 403 | 已认证但无权限 | 越权访问他人房间、非房主审批、非 joined 成员记账（C1/B4/B6） |
| 404 | 资源不存在 | 房间/账单/帖子不存在 |
| 409 | 状态冲突 | 重复申请、超员、结算后改账单、重复结算（B5） |
| 422 | 入参校验失败 | 金额 ≤ 0、participant 为空（FastAPI 默认） |

**403 与 404 的取舍（安全考量）**：越权访问他人房间返回 **403 而非 404**。V1 取"明确告知无权限"，便于 C1 断言；代价是暴露了"该资源存在"这一信息。若未来要收敛信息面，可统一改为 404——那属于铂金档的加固项，此处**显式记录该取舍**。

---

## 6. 任务分解（实现顺序）

| # | 任务 | 负责 | 依赖 |
|---|---|---|---|
| T1 | 仓库骨架：`.gitignore` / `.env.example` / `docker-compose.yml`（db+backend）/ Dockerfile / `config.py`（缺环境变量即启动失败）/ Alembic 初始化 / `users` 表迁移 | Owner | — |
| T2 | 认证：register / login / me，bcrypt 哈希，JWT 签发与校验，`get_current_user` 依赖 | Owner | T1 |
| T3 | 搭子帖：CRUD + 列表分页 + 仅帖主可删 | Owner | T2 |
| T4 | 房间与成员：建房间、申请、审批、退出、四态流转、部分唯一索引迁移、房间级权限依赖 | Owner | T3 |
| T5 | 账单与结算：均分最大余额法（`services/split.py`）、账单增删、结算幂等、结算后只读 | Owner | T4 |
| T6 | 后端测试：pytest 覆盖 T2-T5；`test_split_precision.py`（B3）、`test_idor.py`（C1）必做 | Owner | T5 |
| T7 | 前端骨架：Vite+TS+Tailwind、axios 实例与拦截器、`useAuth`、路由与登录守卫、登录注册页 | Owner | — |
| T8 | 找搭子列表页 + 帖子详情页（发帖、申请加入、创建房间） | Owner | T7 |
| T9 | 房间页：成员区 / 记账区 / 结算区三分区 | Owner | T8 |
| T10 | 前端容器化：多阶段构建 + nginx 静态托管 + `/api` 反代；接入 `docker-compose.yml` | Owner | T9 |
| T11 | QA 验收：独立执行 A1-A5 / B1-B6 / C1-C6，输出验收报告 | Owner（独立复核） | T6, T10 |
| T12 | 红队审计：只报不改，逐条标 成立 / 需修正 / 无法验证 | Owner（独立复核） | T11 |

**并行安排**：T1-T6（后端）与 T7-T10（前端）可并行，契约已在 §5 冻结；T10 需要 T9 完成后接入 compose。

---

## 7. 决策记录（V1）

> **权威表在 `docs/decisions.md`（D1–D21）—— 本文件不再复制决策表，避免两份表漂移。**
>
> 历史：此处曾维护一份 D1–D17 的副本，与 `decisions.md`（当时已到 D21）**长期不一致**。
> 2026-10-12 核实后移除副本，改为此指针，遵循项目自定的"Single Source of Truth"原则。

**与本文档强相关的决策索引**（完整论证见 `decisions.md`）：

| 决策 | 与本文档的关系 |
|---|---|
| D1 / D4 / D5 / D6 | §1 技术选型 |
| D2 / D3 / D17 | §1.1 前端服务形态 |
| D7 / D8 / D9 | §3.1 金额表示、§4.2 分摊规则 |
| D10 | §4.3 结算规则（结算后只读） |
| **D20** | §3.2 表结构、§5.5 账单接口的 **ID 空间约定** |
| D16 | §5.7 错误码语义（越权用 403） |

---

## 8. 待明确事项

| # | 事项 | 影响 | 需要谁定 |
|---|---|---|---|
| O1 | ~~**项目名称**~~ | 目录名、容器名、页面标题、仓库名 | **已定：SplitWay · 分途**（见 D18）；本地目录与仓库名均已统一 |
| O2 | 是否新建独立 GitHub 仓库、公开还是私有 | D14 的 CI 落地位置 | Owner |
| O3 | 房间页移动端适配是否纳入 V1 | 原为 P2；若纳入会挤占工期 | Owner |
| O4 | 账单删除权限是否放宽到"付款人本人也可删" | 当前裁定仅房主 | Owner 可推翻 |
