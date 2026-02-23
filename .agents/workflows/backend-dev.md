---
description: Backend development rules - FastAPI DDD modular monolith conventions
---

# 后端开发规范

本项目后端使用 **FastAPI + SQLAlchemy 2.0 (Async) + Pydantic V2**。
遵循 Modular Monolith + DDD 分层架构。

## 目录结构

```
app/
├── main.py                 # 入口
├── api/v1/router.py        # V1 版本路由汇总（版本号在此管理）
├── bootstrap/              # 应用工厂、生命周期、日志
├── core/                   # 全局配置（Settings）
│   └── security/           # JWT + 密码哈希
├── common/                 # 共享内核
│   ├── entity/base.py      # BaseEntity (UUID PK + AuditMixin)
│   └── exceptions/         # 自定义异常 + 全局处理器
├── infra/                  # 基础设施实现
│   ├── db/                 # SQLAlchemy 引擎 + Session
│   ├── cache/              # Redis
│   └── storage/            # 对象存储适配器 (Local/MinIO/S3/OSS)
└── modules/                # 业务领域模块
    └── <module>/
        ├── api/            # 路由 + 依赖注入
        │   ├── endpoints.py
        │   └── dependencies.py  # 模块 DI 入口（唯一定义处）
        ├── models/         # SQLAlchemy 实体
        ├── schemas/        # Pydantic 数据传输对象
        ├── repositories/   # 仓储接口 + 实现
        ├── services/       # 业务逻辑编排
        └── tasks.py        # Celery 异步任务
```

## 核心规则

### 依赖注入

- 每个模块的 `get_<module>_service` 仅在 `api/dependencies.py` 定义一次
- 其他文件使用 `from .dependencies import get_<module>_service`
- 禁止在 endpoint 文件中重复定义工厂函数

### API 版本管理

- `settings.API_PREFIX = "/api"` 只定义前缀
- 版本号 `/v1`, `/v2` 在 `api/v1/router.py` 的 `APIRouter(prefix="/v1")` 管理
- 新版本：创建 `api/v2/router.py`，在 `application.py` 中追加挂载

### 异常处理

- Service 层抛出 `BaseAPIException` 子类（`NotFoundException`, `ValidationException`, `AuthorizationException`）
- 禁止抛出原生 `ValueError` / `KeyError` 等
- 全局异常处理器已在 `application.py` 注册，endpoint 无需 try/except 业务异常

### 数据库

- 所有表继承 `BaseEntity`（UUID PK + 审计字段 + 软删除）
- 表结构迁移由 Alembic 管理，禁止在 lifespan 中使用 `create_all`
- 全部使用 Async ORM (`AsyncSession`)

### 存储

- 禁止使用 `open()` 内置函数操作文件
- 通过 `StorageAdapter` 接口操作（Local/MinIO/S3/OSS）

## 新增模块模板

创建新模块时，按以下结构初始化：

```bash
modules/<module_name>/
├── __init__.py
├── api/
│   ├── __init__.py
│   ├── dependencies.py    # get_<module>_service
│   └── <resource>.py      # 路由 endpoints
├── models/
│   ├── __init__.py
│   └── <entity>.py
├── repositories/
│   ├── __init__.py
│   └── <module>_repository.py   # ABC 接口 + SQLAlchemy 实现
├── schemas/
│   ├── __init__.py
│   └── <entity>.py
├── services/
│   ├── __init__.py
│   └── <module>_service.py
└── tasks.py
```

然后在 `api/v1/router.py` 中注册新路由。
