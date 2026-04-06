# SAMS 开发任务清单

> 基于架构审查（2026-04-04）生成  
> 优先级：P0=阻断/安全 | P1=核心功能 | P2=重要功能 | P3=完善

---

## P0 — 安全 & 工程基础（立即修复）

| # | 任务 | 文件 | 说明 |
|---|------|------|------|
| P0-1 | `SECRET_KEY` 改为必填，无默认值 | `backend/app/core/config.py` | 防止生产环境使用弱密钥 |
| P0-2 | 添加 `pydantic-settings` 到依赖 | `backend/pyproject.toml` | 当前依赖声明缺失 |
| P0-3 | 创建 `.env.example` | `backend/.env.example` | 列出所有必需环境变量及说明 |
| P0-4 | 修复 Service 层直接操作 db | `backend/app/modules/iam/services/iam_service.py` | `commit()` / `refresh()` 应封装在 Repository 中 |
| P0-5 | 修复 `upload_avatar` 同步存储调用 | `iam_service.py::upload_avatar` | 使用 `run_in_executor` 或异步 storage |

---

## P1 — AI/RAG 基础设施（核心差异化功能）

### T1.1 后端 AI 模块搭建

| # | 任务 | 目标路径 |
|---|------|----------|
| T1.1-1 | 在 `Settings` 中添加 AI 配置项 | `AI_PROVIDER`、`OPENAI_API_KEY`、`EMBEDDING_MODEL`、`EMBEDDING_DIMENSION` |
| T1.1-2 | 创建 `backend/app/infra/ai/` 基础设施层 | LLM 客户端、Embedding 客户端工厂 |
| T1.1-3 | 创建 `backend/app/modules/ai/` 模块 | `models/` (向量存储记录)、`services/` (RAG pipeline)、`api/routes.py` |
| T1.1-4 | 实现档案文档向量化 pipeline | 文本提取 → Embedding → pgvector 存储 |
| T1.1-5 | 实现 RAG 检索问答接口 | `POST /api/v1/ai/chat` - 接收问题，返回基于档案内容的回答 |
| T1.1-6 | 实现流式 SSE 响应 | 大模型流式输出，支持前端 `RagChatPanel.vue` |
| T1.1-7 | 在 alembic env.py 注册 AI 模型 | 向量表迁移 |

### T1.2 前端 RAG 对接

| # | 任务 | 目标文件 |
|---|------|----------|
| T1.2-1 | 创建 `api/ai.ts` | 封装 `/ai/chat`、`/ai/search` 调用 |
| T1.2-2 | 完善 `RagChatPanel.vue` | 流式消息渲染、历史记录、引用来源展示 |
| T1.2-3 | 完善 `AiAssistant.vue` | 浮动助手入口，调用 RAG 接口 |

---

## P1 — 档案库模块（Repository）

> 全宗 → 案卷 → 文件，这是档案管理的核心业务域

| # | 任务 | 目标路径 |
|---|------|----------|
| T2-1 | 设计档案层级数据模型 | `modules/repository/models/`：`Fonds`（全宗）、`ArchiveFile`（案卷）、`ArchiveItem`（文件条目） |
| T2-2 | 实现 Repository 层 CRUD | `modules/repository/repositories/` |
| T2-3 | 实现 Repository 业务服务 | `modules/repository/services/`：归档、检索、层级遍历 |
| T2-4 | 实现 REST API | `modules/repository/api/routes.py`，注册到 `v1_router` |
| T2-5 | 实现 AIP 与 SIP 关联逻辑 | SIP 审批通过后自动生成 AIP 并入档案库 |
| T2-6 | 注册到 alembic | `alembic/env.py` import repository models |
| T2-7 | 前端档案库页面 | `pages/admin/repository/` 树形档案层级浏览 |

---

## P1 — Elasticsearch 全文检索集成

| # | 任务 | 目标路径 |
|---|------|----------|
| T3-1 | 添加 ES 配置到 Settings | `ELASTICSEARCH_URL`，默认 `http://localhost:9200` |
| T3-2 | 创建 `infra/search/` ES 客户端 | 使用 `elasticsearch-py` async 客户端 |
| T3-3 | 实现档案索引服务 | 档案入库时自动索引到 ES |
| T3-4 | 实现全文检索接口 | `GET /api/v1/utilization/search` |

---

## P1 — Celery 异步任务配置

| # | 任务 | 目标路径 |
|---|------|----------|
| T4-1 | 添加 RabbitMQ 配置到 Settings | `RABBITMQ_URL`，默认 `amqp://guest:guest@localhost:5672//` |
| T4-2 | 创建 `backend/celery_app.py` | Celery 实例，使用 RabbitMQ broker + Redis result backend |
| T4-3 | 迁移四性检测为 Celery 任务 | `modules/preservation/tasks.py` |
| T4-4 | 迁移文档向量化为 Celery 任务 | `modules/ai/tasks.py` |
| T4-5 | 添加 docker-compose celery worker 服务 | 或提供 `celery worker` 启动命令文档 |

---

## P2 — 利用服务模块（Utilization）

| # | 任务 | 说明 |
|---|------|------|
| T5-1 | 实现档案检索服务 | 结合 ES 全文检索 + pgvector 语义搜索 |
| T5-2 | 实现档案申请/审批流程 | 公众申请查档 → 管理员审批 → 发放 |
| T5-3 | 实现水印服务 | 下载档案时自动添加溯源水印 |
| T5-4 | 搭建公众门户前端 | `frontend/public-portal/`（独立 Nuxt 应用） |
| T5-5 | 对接 OAuth2 public-portal 客户端 | SSO 登录公众门户 |

---

## P2 — 四性检测引擎完善

| # | 任务 | 说明 |
|---|------|------|
| T6-1 | 实现真实性（Authenticity）检测 | 哈希校验，签名验证 |
| T6-2 | 实现完整性（Integrity）检测 | 文件结构校验，元数据完整性 |
| T6-3 | 实现可用性（Availability）检测 | 文件可读性，格式合规检测 |
| T6-4 | 实现安全性（Security）检测 | 访问控制，加密状态检测 |
| T6-5 | 集成 Celery 异步执行 | 四性检测为耗时任务，需异步 |

---

## P2 — 测试覆盖

| # | 任务 | 目标 |
|---|------|------|
| T7-1 | 建立测试基础设施 | `tests/conftest.py`：测试 DB、mock fixtures |
| T7-2 | IAM 单元测试 | 认证、注册、权限校验 |
| T7-3 | OAuth2 集成测试 | 授权码流程、token 刷新 |
| T7-4 | SIP 提交流程测试 | 提交、审核、状态流转 |
| T7-5 | RAG 接口测试 | 向量检索、问答响应 |
| T7-6 | 目标覆盖率 80%+ | pytest-cov |

---

## P3 — 工程质量完善

| # | 任务 | 说明 |
|---|------|------|
| T8-1 | CORS 添加开发默认配置 | `BACKEND_CORS_ORIGINS` 本地开发默认包含 localhost:3000/3001 |
| T8-2 | `stats.py` 异常改为 warning log | 替换 `except Exception: pass` |
| T8-3 | 对接 `ui_design/` 设计稿 | 按设计稿实现各业务页面 |
| T8-4 | 添加 OIDC UserInfo 端点 | `GET /oauth/userinfo` 标准端点 |
| T8-5 | 添加 API 版本 prefix 到 WS | WebSocket 路径统一为 `/api/v1/ws` |
| T8-6 | 生产部署文档 | Nginx 配置、HTTPS、环境变量清单 |

---

## 建议开发顺序

```
阶段 1（当前冲刺）：P0 安全修复 → AI/RAG 基础设施 → Elasticsearch 集成
阶段 2：Repository 档案库模块 → Celery 任务队列 → 测试覆盖
阶段 3：Utilization 利用服务 → 四性检测引擎 → 公众门户前端
阶段 4：性能优化 → 生产部署 → 完整文档
```
