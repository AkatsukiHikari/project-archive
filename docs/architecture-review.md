# SAMS 架构审查报告

> 审查日期：2026-04-04  
> 审查范围：backend（FastAPI/DDD）、frontend（Nuxt 4）、基础设施（docker-compose）

---

## 一、项目理解

SAMS（Smart Archive Management System）是一个面向政府/企业的智能档案管理平台，核心特征：

- **标准遵从**：中国档案行业标准（DA/T），覆盖 SIP 提交、四性检测、档案库管理
- **AI RAG**：基于 pgvector 的向量检索 + 大模型问答
- **多租户 SaaS**：租户隔离的 IAM（用户、角色、组织、菜单）
- **SSO**：自建 OAuth2 授权码 + PKCE，支持多前端应用
- **技术栈**：FastAPI + PostgreSQL(pgvector) + Redis + RabbitMQ + Elasticsearch + MinIO；前端 Nuxt 4 + shadcn-nuxt + Pinia

---

## 二、已完成的部分（做得好的地方）

### 基础设施
- `docker-compose.yml` 完整，包含 pgvector/pg17、Redis 7.4、RabbitMQ 3.13、ES、MinIO，版本合理
- 使用 `pgvector/pgvector:pg17` 镜像，RAG 向量搜索已具备数据库基础
- 健康检查 (`healthcheck`) 配置完整

### 后端 DDD 分层
- 每个模块严格遵循 `api/` → `services/` → `repositories/` → `models/` + `schemas/` 分层
- `BaseEntity` + `AuditMixin`：UUID 主键、软删除、审计字段，所有实体统一继承
- `ResponseModel` 统一响应格式 `{code, data, message}`，成功固定 `code=0`
- 异步彻底：全部 `async def`，`AsyncSession`，`asyncpg` 驱动
- 多租户设计已在 User、Role、SIPRecord 等核心实体上落实 `tenant_id`

### IAM / SSO
- OAuth2 授权码 + PKCE 流程完整（`/oauth/authorize` → `/oauth/login` → `/oauth/token`）
- 登录 IP 限速（Redis 计数，10次失败触发15分钟封禁）
- RBAC：User → Role → Menu(Permission) 三级，`require_permissions` 装饰器
- WebSocket 实时通知，JWT 认证，心跳机制完善

### 前端
- Nuxt 4，Composition API，`<script setup lang="ts">` 统一
- Pinia store（user, permission, notification）
- OAuth2 callback 处理完整（`/auth/callback.vue`）
- 存在 `RagChatPanel.vue`、`AiAssistant.vue` 等 AI 相关组件（待接后端）
- `ui_design/` 目录下有完整 UI 稿（HTML+截图），可作为实现参考

---

## 三、架构问题与缺口

### 🔴 严重（阻断核心功能）

#### 1. AI/RAG 模块完全缺失
- pgvector 已就绪，但后端无 `ai` 或 `rag` 模块
- 无嵌入（embedding）服务、无向量存储操作、无检索增强生成（RAG）管道
- 无 LLM 客户端集成（OpenAI/Anthropic/本地模型）
- `Settings` 中无任何 AI 相关配置项（API Key、模型名、Embedding 维度等）
- 前端 `RagChatPanel.vue`、`AiAssistant.vue` 无后端支撑，功能断路

#### 2. `repository` 模块（档案库）为空
- `backend/app/modules/repository/` 下仅有空 `__init__.py`
- 档案库是核心业务域：全宗（Fonds）→ 案卷（File）→ 文件（Item）层级体系未实现
- AIP（存档包）管理逻辑缺失

#### 3. `utilization` 模块（利用服务）为空
- `backend/app/modules/utilization/` 下仅有空 `__init__.py`
- 档案检索、水印服务、公众查档门户入口未实现
- 依赖 Elasticsearch，但 ES 客户端未集成（见下）

#### 4. Elasticsearch 未集成
- `docker-compose.yml` 有 ES，但 `backend/app/infra/` 无 ES 客户端
- `Settings` 中无 `ELASTICSEARCH_URL` 等配置
- 档案全文检索功能无法实现

#### 5. Celery 异步任务未配置
- `pyproject.toml` 有 `celery[redis]`，RabbitMQ 在 docker 中启动
- 无 `celery_app.py` / `worker.py`，无任务注册
- 四性检测、档案格式转换等耗时任务需要异步队列

---

### 🟠 高优先级

#### 6. 安全：`SECRET_KEY` 有不安全默认值
```python
SECRET_KEY: str = "sams_secret_key"  # config.py line 52
```
应改为必填项（无默认值），启动时若未设置则报错退出。

#### 7. `pydantic-settings` 未列入依赖
- `config.py` 使用 `from pydantic_settings import BaseSettings`
- `pyproject.toml` 中未声明 `pydantic-settings` 依赖

#### 8. 零测试覆盖率
- `pyproject.toml` 配置了 pytest，但无任何测试文件
- 需要至少覆盖：IAM 认证、OAuth2 流程、SIP 提交、四性检测

#### 9. 服务层违反 Repository 抽象
- `iam_service.py` 多处直接调用 `self.repository.db.commit()` / `db.refresh()`
- 正确做法：commit 应封装在 Repository 或 UnitOfWork 中
- 涉及位置：`update_user_profile`（L85）、`upload_avatar`（L131-138）、`update_user_password`（L157）

#### 10. 存储操作在异步上下文中同步调用
- `iam_service.py::upload_avatar` 调用 `storage.save(...)` 无 `await`
- 需确认 StorageAdapter 是否为同步实现（若是则需用 `run_in_executor`）

---

### 🟡 中优先级

#### 11. 无 `.env.example`
- 开发者无法得知需要哪些环境变量，影响协作和部署

#### 12. 公众门户前端缺失
- `Settings.OAUTH_CLIENTS` 中注册了 `public-portal`（公众查档门户）
- 但 `frontend/` 下只有 `admin-web`，公众门户未创建

#### 13. 缺少 RabbitMQ、ES 配置项
- `Settings` 中无 `RABBITMQ_URL`、`ELASTICSEARCH_URL`
- 服务启动时无法通过配置切换这些基础设施连接

#### 14. CORS 默认为空列表
- `BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = []` 
- 本地开发时需手动配置，建议提供开发默认值或文档说明

#### 15. `repository` 和 `utilization` 未注册到 alembic
- `alembic/env.py` 未 import 这两个模块的 models
- 实现后需同步更新，否则 migration 无法检测到新表

---

### 🟢 低优先级

#### 16. `stats.py` 静默吞掉异常
```python
except Exception:
    pending_sips = 0  # stats.py line 71
```
应至少 `logger.warning()` 记录异常原因。

#### 17. `ui_design/` HTML 稿未与页面对接
- 5 个高质量 UI 设计稿（含 RAG、四性检测、公众门户等）存放在 `frontend/admin-web/ui_design/`
- 可作为实现各页面的直接参考，建议在开发前先对照设计稿

#### 18. `SECRET_KEY` 应通过 `.env` 强制注入

---

## 四、模块完成度评估

| 模块 | 完成度 | 说明 |
|------|--------|------|
| IAM（用户/角色/组织/菜单/租户） | ✅ ~85% | 基本完整，缺测试 |
| OAuth2 SSO | ✅ ~90% | 流程完整，缺 OIDC UserInfo 端点 |
| Notification（通知） | ✅ ~70% | 基本实现，WebSocket 推送完整 |
| Audit（审计日志） | ✅ ~70% | 基础完成 |
| Schedule（任务调度） | ✅ ~60% | CRUD 完整，无 Celery 集成 |
| Collection（SIP 归档提交） | 🟡 ~40% | 模型和 CRUD 有，处理流程待完善 |
| Preservation（四性检测） | 🟡 ~30% | 模型和 CRUD 有，检测引擎未实现 |
| Repository（档案库管理） | 🔴 ~0% | 仅空目录 |
| Utilization（查档利用） | 🔴 ~0% | 仅空目录 |
| AI/RAG | 🔴 ~0% | 完全缺失 |
| 前端 admin-web | 🟡 ~50% | IAM管理完整，业务页面待实现 |
| 前端 public-portal | 🔴 ~0% | 不存在 |

---

## 五、整体评价

**基础架构设计合理**，DDD 分层规范，多租户/SSO/RBAC 已成熟，可以直接在此基础上继续开发。主要问题是**业务核心域（档案库、利用服务）和 AI/RAG 模块完全缺失**，以及若干安全和工程质量问题需修复。

优先级建议：先补齐安全问题 → 再建立 AI/RAG 基础设施 → 再实现 repository/utilization 业务域。
