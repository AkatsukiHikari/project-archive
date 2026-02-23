# Project Context: Smart Archive Management System (SAMS)

## 1. Role & Objective
You are an expert Full-Stack Software Architect and Lead Developer.
Your goal is to assist in building the **Smart Archive Management System (SAMS)**, a comprehensive platform for government/enterprise archives.
The system must be secure, high-performance, and adhere to Chinese Archive Standards (DA/T).

## 2. Technology Stack (Strict Constraints)

### Frontend (The "User Layer")
* **Framework:** Nuxt 3 (Vue 3 Composition API, `<script setup>`).
* **Styling:** Tailwind CSS (Utility-first).
* **UI Library:** **shadcn-vue** (Using `shadcn-nuxt` module for integration).
    * *Note:* This is a copy-paste component architecture. Components reside in `components/ui`.
* **Icons:** **Lucide Icons** (Standard for shadcn) or Phosphor Icons.
* **State Management:** Pinia.
* **Data Fetching:** Nuxt `useFetch` / `$fetch`.
* **Forms:** `vee-validate` + `zod` (for schema validation, integrates well with shadcn form components).

### Backend (The "Logic Layer")
* **Framework:** FastAPI (Python 3.10+).
* **ORM:** SQLAlchemy 2.0+ (Async mode only).
* **Schema Validation:** Pydantic V2.
* **Database:** PostgreSQL 15+ (with `pgvector` extension for AI RAG features).
* **Migrations:** Alembic.
* **Search Engine:** Elasticsearch 8.x.
* **Task Queue:** Celery (with RabbitMQ as Broker, Redis as Result Backend).
* **Cache:** Redis.

### Dev & Ops
* **Package Manager:** `pnpm` (Frontend), `poetry` or `uv` (Backend).
* **Containerization:** Docker Compose.

## 3. Coding Conventions

### General
* **Language:** Logic in English, Comments/Documentation in Chinese (for local team understanding) or English.
* **Type Hinting:** Mandatory for both Python (Type hints) and TS (Interfaces/Types).

### Backend (Python/FastAPI)
* Use **Async/Await** for all I/O operations.
* Follow **RESTful** API design patterns.
* Structure: `app/api/v1/endpoints`, `app/core`, `app/db`, `app/schemas`, `app/services`.
* Use **Dependency Injection** (`Depends`) for DB sessions and Services.
* **Error Handling:** Use global exception handlers and standardized JSON error responses.

### Frontend (Nuxt/Vue)
* Use **Composition API** exclusively.
* Use **TypeScript** for all components.
* **Component Structure:**
    * `components/ui/*`: Base shadcn components (Buttons, Inputs, Dialogs).
    * `components/business/*`: Complex business components (e.g., `ArchiveUploadForm.vue`, `FourNatureReport.vue`).
* Ensure **Responsive Design** (Mobile/Tablet/Desktop) using Tailwind classes.

## 4. Functional Requirements (SRS V3.0)

The implementation must strictly follow these business modules:

### Module 1: Platform Infrastructure (Foundations)
* **IAM:** Multi-tenant support (Bureau-Archive-Office), SSO integration, RBAC with "Three-Safety-Personnel" (Admin, Security, Auditor) separation.
* **Audit:** Log every view, download, and print action.

### Module 2: The "4-Natures" Detection Service (Middleware)
* **Independent Service:** Must be a standalone module/service callable by other parts.
* **Check Items:**
    1.  **Authenticity:** Metadata completeness, Electronic signature verification.
    2.  **Integrity:** MD5/SHA256 hash verification against metadata.
    3.  **Usability:** File format check (PDF/A, OFD whitelist), Virus scan (ClamAV stub).
    4.  **Safety:** Sensitive word filtering (AI/NLP based).

### Module 3: Resource Collection (Ingest)
* **Online:** API for OA system integration (receive OFD/PDF).
* **Offline:** SIP (ZIP package) upload -> Unzip -> Trigger 4-Natures Check -> Staging Area.
* **Staging:** "Pre-archive" buffer zone for manual/AI review before formal entry.

### Module 4: Archive Management (AMS Core)
* **AI Processing:** OCR extraction -> Auto-fill Metadata -> Auto-classification.
* **Management:** Fonds -> Category -> Year -> Retention Period hierarchy.
* **Appraisal:**
    * **Retention:** Auto-flag expired archives for destruction.
    * **Openness (Red/Green Light):** Auto-scan text for sensitive words. Red=Control, Green=Open.

### Module 5: Utilization Service (Public/Staff)
* **Search:** Elasticsearch powered full-text search + Vector Search (RAG) for semantic questions.
* **Staff UI:** Dual-screen logic (Staff sees all, Guest sees sanitized view).
* **Watermarking:** Dynamic watermarks (User+IP+Time) on all previews.

## 5. Development Roadmap (Phase 1 Focus)
We are starting with **Phase 1: Foundation & Detection**.
1.  Setup Monorepo (Frontend/Backend).
2.  Design Database Schema (PostgreSQL) for Users, Logs, and File Records.
3.  Implement "4-Natures Detection" Micro-logic (Hash calc, Virus scan mock, Format check).
4.  Build Basic Layout (Nuxt + shadcn-vue) and Login Screen.

---
**Instruction for AI:**
When asked to write code, always refer to the "Tech Stack" and "Coding Conventions". When asked about logic, refer to "Functional Requirements". Start by helping me setup the project structure.


## 6. Project Architecture & Directory (Enterprise DDD)

### Architecture Pattern
* **Style:** Modular Monolith with Domain-Driven Design (DDD) principles.
* **Layering:**
    * **Interface Layer:** `router.py` (API definitions).
    * **Application Layer:** `service.py` (Business orchestration, transaction management).
    * **Domain Layer:** `models.py` (Entities), `schemas.py` (Data transfer).
    * **Infrastructure Layer:** `infra/` (Db, Storage, Search, Celery implementation details).

### Directory Tree (Strict)
project-memoria/
├── backend/ (Backend)
│   ├── app/
│   │   ├── bootstrap/          # Lifespan, Logging setup
│   │   ├── common/             # Shared Kernel (BaseEntity, R.success, Exceptions)
│   │   ├── core/               # Global Config (Settings)
│   │   ├── infra/              # Infrastructure Implementations
│   │   │   ├── storage/        # Storage Adapters (Local/MinIO)
│   │   │   ├── security/       # JWT, Password Hashing
│   │   │   └── celery/         # Async Worker Config
│   │   ├── modules/            # Business Domains (OAIS Model)
│   │   │   ├── iam/            # Users, Roles, RBAC
│   │   │   ├── collection/     # Ingest, SIP Parsing, Staging
│   │   │   ├── repository/     # AIP Management, Fonds, Appraisal
│   │   │   ├── preservation/   # 4-Natures Detection Engine
│   │   │   └── utilization/    # Search, Orders, Watermarking
│   │   └── main.py
│
└── frontend/ (Frontend - Monorepo)
    ├── packages/shared/        # Shared Types, Utils
    └── apps/
        ├── admin-deck/         # Management Console (Nuxt + shadcn)
        └── kiosk-portal/       # Self-service Terminal (Nuxt Touch)

## 7. Coding Standards (Strict)
1.  **UUID as Primary Key:** All database tables must use UUID (v7 preferred, or v4) as the primary key to ensure security and uniqueness across distributed systems.
2.  **Audit Columns:** Every table must inherit `AuditMixin` (`create_time`, `update_time`, `create_by`, `is_deleted`). **Soft delete** is mandatory.
3.  **Storage Abstraction:** Never use `open()` built-in. Use `StorageAdapter.save()`.
4.  **Type Hinting:** 100% coverage required.