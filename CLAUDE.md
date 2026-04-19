# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**SAMS** (Smart Archive Management System) — a full-stack platform for government/enterprise archive management adhering to Chinese Archive Standards (DA/T). Modular monolith with DDD layering.

---

## Commands

### Infrastructure (start first)
```bash
docker-compose up -d   # Start PostgreSQL, Redis, RabbitMQ, Elasticsearch, MinIO
docker-compose down    # Stop services
```

### Backend
```bash
cd backend
uv sync                                              # Install dependencies
python app/main.py                                   # Dev server on :8000 (auto-reload)
uvicorn app.main:app --reload                        # Alternative
alembic upgrade head                                 # Apply migrations
alembic revision --autogenerate -m "description"    # Generate migration
pytest tests/                                        # Run all tests
pytest tests/path/to/test_file.py::test_name        # Run single test
black app/ && isort app/                             # Format code
```

### Frontend
```bash
cd frontend/admin-web
pnpm install      # Install dependencies
pnpm dev          # Dev server on :3000 (proxies /api and /oauth to :8000)
pnpm build        # Production build
pnpm lint         # ESLint
```

---

## Architecture

### Backend: DDD Layered Modules

```
backend/app/
├── bootstrap/       # App factory (application.py), lifespan hooks
├── common/          # Shared kernel: BaseEntity, ResponseModel, error codes, exceptions
├── core/            # Global Settings (config.py), security (JWT, RBAC)
├── infra/           # Infrastructure: db/session.py, cache/redis.py, storage/, ws/
├── modules/         # Business domains
│   ├── iam/         # Users, Roles, Tenants, Orgs, Menus, SSO/OAuth
│   ├── audit/       # Audit log
│   ├── notification/ # System notifications
│   ├── schedule/    # Task scheduling
│   ├── collection/  # Archive ingest (SIP, staging)
│   ├── repository/  # AIP management, fonds hierarchy
│   ├── preservation/ # 4-Natures detection engine
│   └── utilization/ # Search, watermarking, public access
└── api/v1/router.py # Top-level route assembly; all routes require get_current_user
```

Each module follows: `api/` (routes) → `services/` (business logic) → `repositories/` (data access) → `models/` (SQLAlchemy entities) + `schemas/` (Pydantic DTOs).

### Frontend: Nuxt SPA

```
frontend/admin-web/
├── api/          # Axios-based API client modules (iam.ts, schedule.ts, etc.)
├── stores/       # Pinia stores (user, permission, notification)
├── pages/admin/  # Auto-routed pages
├── components/
│   ├── ui/       # shadcn-nuxt base components (copy-paste architecture)
│   └── business/ # Complex domain-specific components
├── layouts/      # admin.vue shell layout
├── middleware/   # auth.ts (authentication guard)
└── utils/axios/  # Axios instance + interceptors (service.ts)
```

---

## Key Patterns & Conventions

### Backend

- **All I/O must be async/await** — use `AsyncSession`, `async def` endpoints.
- **UUID primary keys** on all tables (v4/v7). All tables inherit `AuditMixin` (`create_time`, `update_time`, `create_by`, `is_deleted`). **Soft delete is mandatory** (`is_deleted` flag, never `DELETE`).
- **Storage**: Never use Python's `open()`. Always use `StorageAdapter.save()`.
- **Response format**: All endpoints return `ResponseModel(code, data, message)`. Success is `code=0`.
- **Error codes**: Hierarchical by domain — 1000s IAM, 2000s Collection, 3000s Repository, 4000s Preservation, 5000s Utilization, 9000s Validation, 9999 Internal.
- **RBAC**: Use `require_permissions(*perms)` decorator from `app/core/security/permissions.py`. Users `admin`/`superadmin` bypass all checks.
- **Dependency injection**: DB session via `get_db()`, current user via `get_current_user` from `app/modules/iam/api/dependencies.py`.
- **Type hints**: 100% coverage required.

### Frontend

- **Composition API only** — all components use `<script setup lang="ts">`.
- **shadcn-nuxt** for UI primitives; add new components via `npx shadcn-vue@latest add <component>`.
- **Forms**: `vee-validate` + `zod` for schema validation.
- **Data fetching**: Nuxt `useFetch` / `$fetch` for SSR-aware calls; Axios (`utils/axios/service.ts`) for imperative calls.

### Database Migrations

Migration files use timestamp naming: `YYYY_MM_DD_HHMM-<rev>_<slug>.py`. When adding a new module, import its models in `alembic/env.py` alongside existing imports.

---

## Environment

Backend reads from `backend/.env`. Key variables:

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | PostgreSQL async connection string |
| `REDIS_HOST/PORT` | Redis cache |
| `STORAGE_TYPE` | `local` / `minio` / `aws` / `alioss` |
| `SECRET_KEY` | JWT signing key |
| `CORS_ORIGINS` | Allowed frontend origins |

