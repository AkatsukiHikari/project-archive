# SAMS 智慧档案管理系统 — 全新环境部署手册

> 命令里出现 `<...>` 的地方需要你按实际情况替换。

---

## 0. 这套系统由哪些部分组成

| 组成 | 说明 | 怎么跑 |
|---|---|---|
| **基础设施**（PostgreSQL / Redis / RabbitMQ / Elasticsearch / MinIO / Ollama / Celery worker） | 数据库、缓存、消息队列、全文检索、对象存储、本地大模型 | 根目录 `docker-compose.yml`（Docker） |
| **后端 API** | FastAPI（Python），端口 `:8000` | **原生运行**（uv），不在 docker-compose 里 |
| **前端** | Nuxt 4（Vue3），端口 `:3000` | **原生运行**（pnpm） |
| **Dify（AI 平台）** | 独立的官方部署，提供 OCR / 问答 / 智能著录的工作流 | 独立 Docker（`dify/docker/`）+ 一次性初始化脚本 |

> ⚠️ 注意：后端 API 和前端是**原生跑**的（不是 Docker）。docker-compose 里只有基础设施 + Celery worker + Ollama。

---

## 1. 前置要求（先装好这些）

- **Docker** + **Docker Compose**（跑基础设施和 Dify）
- **uv**（Python 包管理 / 运行器）—— 后端用
- **Node.js ≥ 20** + **pnpm**—— 前端用
- 机器内存建议 ≥ 16G（Elasticsearch + Dify 比较吃内存）

---

## 2. 启动基础设施（Docker）

在项目根目录：

```bash
docker compose up -d
```

这会拉起并后台运行：
- `sams-db`（PostgreSQL/pgvector，:5432，账号 `postgres` / `postgres` / 库 `sams`）
- `sams-redis`（:6379）
- `sams-rabbitmq`（:5672，管理台 :15672，guest/guest）
- `sams-elasticsearch`（:9200，单节点、关闭鉴权）
- `sams-minio`（API :9000，控制台 :9001，`minioadmin`/`minioadmin`）
- `sams-ollama`（:11434，本地模型）
- `sams-celery-worker`（后台任务：嵌入、四性检测等）

检查是否都健康：

```bash
docker compose ps
```

> Elasticsearch 索引、MinIO 桶**不用手动建**——后端启动时会自动建 ES 索引，MinIO 桶在首次写文件时自动建。

### 2.1 拉取 Ollama 嵌入模型（知识库语义检索要用）

```bash
docker exec sams-ollama ollama pull nomic-embed-text
```

---

## 3. 后端：配置 + 初始化数据库

```bash
cd backend
uv sync                       # 安装依赖
cp .env.example .env          # 生成配置文件，然后编辑它（见下）
```

### 3.1 编辑 `backend/.env`（至少改这几项）

```ini
# —— 必填 ——
SECRET_KEY=<随便一串足够长的随机字符串，用于 JWT 签名>
ADMIN_EMAIL=admin@sams.local
ADMIN_PASSWORD=<超级管理员初始密码，例如 Admin@2024>

# —— 基础设施（本地默认即可，和 docker-compose 对应）——
POSTGRES_SERVER=localhost
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=sams
REDIS_HOST=localhost
ELASTICSEARCH_URL=http://localhost:9200

# —— 存储：用 MinIO ——
STORAGE_TYPE=minio
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin

# —— AI（先留空，Dify 部署好后回填，见第 6 章）——
DIFY_BASE_URL=http://localhost/v1
DIFY_OCR_WORKFLOW_KEY=
DIFY_QA_API_KEY=
DIFY_CATALOG_WORKFLOW_KEY=
DIFY_DATASET_API_KEY=
DIFY_ARCHIVE_DATASET_ID=
```

> `ADMIN_PASSWORD` 不设的话种子脚本会报错。SECRET_KEY 生产环境务必用强随机值。

### 3.2 跑数据库迁移（建表）

```bash
PYTHONPATH=. uv run alembic upgrade head
```

### 3.3 灌入**必需**的初始数据（顺序无所谓，三个都要跑）

```bash
PYTHONPATH=. uv run python app/scripts/seed.py                 # 租户 / 角色 / 菜单 / 超级管理员账号
PYTHONPATH=. uv run python app/scripts/seed_sys_dicts.py       # 系统字典（密级/保管期限/开放状态/智能著录阈值…）
PYTHONPATH=. uv run python app/scripts/seed_archive_categories.py   # 档案门类 + 字段定义 + 录入排版（著录必需）
```

这三个跑完，系统就能登录、能著录了。**都是幂等的**，重复跑会跳过已存在的数据。

### 3.4 （可选）灌入演示数据

想要一套样例档案/库房/利用/鉴定/编研数据用于演示或测试，可按需跑：

```bash
PYTHONPATH=. uv run python app/scripts/seed_demo_archives.py      # 样例档案
PYTHONPATH=. uv run python app/scripts/seed_organize_demo.py      # 著录整理演示
PYTHONPATH=. uv run python app/scripts/seed_storage_demo.py       # 库房/出入库
PYTHONPATH=. uv run python app/scripts/seed_detection_demo.py     # 四性检测
PYTHONPATH=. uv run python app/scripts/seed_util_demo.py          # 利用/借阅
PYTHONPATH=. uv run python app/scripts/seed_appraisal_demo.py     # 开放鉴定
PYTHONPATH=. uv run python app/scripts/seed_research_demo.py      # 编研
PYTHONPATH=. uv run python app/scripts/seed_collection_demo.py    # 收集移交
PYTHONPATH=. uv run python app/scripts/seed_fulltext_demo.py      # 全文检索样例
```

> 生产环境只跑 3.3 的必需种子，不要跑演示数据。

---

## 4. 启动后端 API

```bash
cd backend
uv run python app/main.py
```

启动后监听 `http://localhost:8000`（自带 `--reload` 热重载）。

> ⚠️ **改了 `.env` 必须完整重启进程**才生效（`--reload` 只热载 `.py` 代码、不会重新读 `.env`）。

---

## 5. 前端

```bash
cd frontend/admin-web
pnpm install
```

**开发模式**（带热更新，会把 `/api`、`/oauth` 代理到 `:8000`）：

```bash
pnpm dev        # http://localhost:3000
```

**生产构建**：

```bash
pnpm build
node .output/server/index.mjs    # 或用进程管理器托管
```

### 访问与登录

- 地址：`http://localhost:3000`
- 默认账号：`admin` / 你在 `.env` 里设的 `ADMIN_PASSWORD`

---

## 6. （可选）部署 Dify，开启 AI 功能

OCR 识别原文、智能问答、智能著录这些 AI 能力依赖 Dify。不需要 AI 可以跳过本章——其余功能照常用。

### 6.1 启动 Dify（官方部署）

```bash
cd dify/docker
cp .env.example .env
```

编辑 `dify/docker/.env`：
- `FILES_URL` 设为**宿主机 IP**（如 `http://192.168.3.101`），不要用 localhost，否则 MinerU/插件取文件会失败。

```bash
docker compose up -d            # 改了 .env 后必须 up -d 重建容器，restart 不读新 env
```

Dify 控制台默认 `http://localhost`，初始管理员按官方流程创建（本项目用 `cloud@admin.com` / `Claude2026`）。

### 6.2 在 Dify 里配两样东西

1. **Embedding 模型**（知识库语义检索需要）：设置 → 模型供应商 → 系统模型设置 → Embedding，选 Ollama 的 `nomic-embed-text`（或 OpenAI `text-embedding-3-small`）。
2. **MinerU 工具**（OCR 用）：安装并配置 MinerU 插件，确保它能连通其解析服务（连不上会报 ConnectTimeout）。

### 6.3 一键创建工作流并回填 key

```bash
cd backend
PYTHONPATH=. uv run python scripts/dify_setup.py --all --purge   # 删旧 + 建 知识库/OCR工作流/问答Chatflow
PYTHONPATH=. uv run python scripts/dify_setup.py --catalog       # 建 智能著录抽取工作流
```

脚本会打印出几个 key，**把它们填进 `backend/.env`**：

```ini
DIFY_OCR_WORKFLOW_KEY=app-xxxx
DIFY_QA_API_KEY=app-xxxx
DIFY_CATALOG_WORKFLOW_KEY=app-xxxx
DIFY_DATASET_API_KEY=dataset-xxxx
DIFY_ARCHIVE_DATASET_ID=xxxx
```

回填后**重启后端 API**（第 4 章），AI 功能即可用。

### 6.4 同步知识库（可选）

进系统「AI 智能功能 → AI 知识库」，点「一键全量同步」，把档案推进 Dify 知识库（需 6.2 的 Embedding 已配好）。

---

## 7. 启动顺序速查（TL;DR）

```bash
# 1) 基础设施
docker compose up -d
docker exec sams-ollama ollama pull nomic-embed-text

# 2) 后端
cd backend
uv sync && cp .env.example .env       # 编辑 .env：SECRET_KEY / ADMIN_PASSWORD
PYTHONPATH=. uv run alembic upgrade head
PYTHONPATH=. uv run python app/scripts/seed.py
PYTHONPATH=. uv run python app/scripts/seed_sys_dicts.py
PYTHONPATH=. uv run python app/scripts/seed_archive_categories.py
uv run python app/main.py             # 跑在 :8000

# 3) 前端（另开一个终端）
cd frontend/admin-web
pnpm install && pnpm dev              # 跑在 :3000

# 4) （可选）Dify + AI：见第 6 章
```

打开 `http://localhost:3000`，用 `admin` / `<ADMIN_PASSWORD>` 登录。

---

## 8. 常见问题

| 现象 | 原因 / 处理 |
|---|---|
| 改了 `.env` 没生效 | `--reload` 不重读 `.env`，**完整重启**后端进程（Ctrl+C 再 `uv run python app/main.py`） |
| 登录后菜单没更新 | 菜单是登录时缓存的，改了菜单/角色后**退出重新登录** |
| ES 报连接失败 | 确认 `sams-elasticsearch` 健康（`docker compose ps`），`.env` 的 `ELASTICSEARCH_URL` 对 |
| 查看原文打不开 | 该档案没挂接数字化成果（PDF/OFD）。原文 = 附件，没附件就没有原文 |
| AI 报"未配置工作流" | `DIFY_*_KEY` 没填或后端没重启（见第 6.3） |
| 知识库同步报 embedding 错 | Dify 没配 Embedding 模型（见 6.2） |
| MinerU OCR ConnectTimeout | Dify 里 MinerU 工具连不上解析服务，检查其 endpoint / 网络 |
| 端口被占用 | 5432/6379/9200/9000/3000/8000 等被占，先 `lsof -i :端口` 排查 |

---

## 9. 数据与备份

- **业务数据**全在 PostgreSQL（`sams` 库）和 MinIO（原文文件）。
- **检索数据**在 Elasticsearch（是 PostgreSQL 的副本，可重建）；如需重建索引，系统内有重建入口（按门类/全宗导航相关页面或后端 ES 同步接口）。
- 备份时备好：Postgres 的 `postgres_data` 卷 + MinIO 的 `minio_data` 卷（docker volume）即可。
