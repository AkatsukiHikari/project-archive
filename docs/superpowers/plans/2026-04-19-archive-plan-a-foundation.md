# 档案管理 Plan A：数据模型 + 基础 CRUD API

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 重构 repository 模块，建立档案门类体系、目录层级和档案主表，提供完整的基础 CRUD API。

**Architecture:** 现有 `repo_archive_file` + `repo_archive_item` 两表替换为新的 `repo_archive_category` / `repo_catalog` / `repo_archive` 三表。档案主表采用 JSON 混合模式：DA/T 必有字段规范化列 + 门类私有字段存 JSONB（GIN 索引）。层级通过 `parent_id` 自引用支持案卷/卷内文件。

**Tech Stack:** FastAPI · SQLAlchemy 2.x Async · PostgreSQL (JSONB + GIN index) · Alembic · Pydantic v2 · pytest + pytest-asyncio

**Spec:** `docs/features/feature_档案管理.md`

---

## 文件清单

### 新建
| 文件 | 职责 |
| --- | --- |
| `backend/app/modules/repository/models/category.py` | `repo_archive_category` ORM 模型 |
| `backend/app/modules/repository/models/no_rule.py` | `repo_archive_no_rule` ORM 模型（Plan B 填充实现） |
| `backend/app/modules/repository/schemas/category.py` | 门类 Pydantic schemas |
| `backend/app/modules/repository/schemas/archive.py` | 档案 Pydantic schemas |
| `backend/app/modules/repository/repositories/category_repo.py` | 门类数据访问层 |
| `backend/app/modules/repository/repositories/archive_repo.py` | 档案数据访问层 |
| `backend/app/modules/repository/services/category_service.py` | 门类业务逻辑 |
| `backend/app/modules/repository/services/archive_service.py` | 档案业务逻辑 |
| `backend/app/modules/repository/api/routes_category.py` | 门类 API 路由 |
| `backend/app/modules/repository/api/routes_archive.py` | 档案 API 路由（含目录） |
| `backend/tests/unit/repository/__init__.py` | 测试包 |
| `backend/tests/unit/repository/test_category_service.py` | 门类服务单元测试 |
| `backend/tests/unit/repository/test_archive_service.py` | 档案服务单元测试 |

### 修改
| 文件 | 变更内容 |
| --- | --- |
| `backend/app/modules/repository/models/archive.py` | 重写：替换旧三层模型为新 `Catalog` + `Archive` |
| `backend/app/modules/repository/models/__init__.py` | 导出新模型 |
| `backend/alembic/env.py` | 导入新模型（触发 autogenerate） |
| `backend/app/api/v1/router.py` | 挂载新路由 |

### 新建 Migration
| 文件 | 内容 |
| --- | --- |
| `backend/alembic/versions/2026_04_19_0001_archive_management_foundation.py` | 创建 5 张新表，保留旧表（不删，等数据迁移确认后再清理） |

---

## Task 1：门类模型 + 目录模型 + 档案模型

**Files:**
- Create: `backend/app/modules/repository/models/category.py`
- Create: `backend/app/modules/repository/models/no_rule.py`
- Rewrite: `backend/app/modules/repository/models/archive.py`
- Modify: `backend/app/modules/repository/models/__init__.py`

- [ ] **Step 1: 写失败测试（模型可实例化）**

```python
# backend/tests/unit/repository/test_models.py
import uuid
import pytest
from app.modules.repository.models.category import ArchiveCategory
from app.modules.repository.models.archive import Catalog, Archive


def test_archive_category_instantiate():
    cat = ArchiveCategory(code="WS", name="文书档案", is_builtin=True)
    assert cat.code == "WS"
    assert cat.is_builtin is True
    assert cat.requires_privacy_guard is False


def test_catalog_instantiate():
    cat = Catalog(
        fonds_id=uuid.uuid4(),
        category_id=uuid.uuid4(),
        catalog_no="1",
        name="2024年度文书目录",
        year=2024,
        org_mode="by_item",
    )
    assert cat.org_mode == "by_item"


def test_archive_instantiate():
    arch = Archive(
        fonds_id=uuid.uuid4(),
        catalog_id=uuid.uuid4(),
        category_id=uuid.uuid4(),
        level="item",
        title="关于XXX的通知",
        year=2024,
        fonds_code="J001",
    )
    assert arch.level == "item"
    assert arch.status == "active"
```

- [ ] **Step 2: 运行测试，确认失败**

```bash
cd backend && pytest tests/unit/repository/test_models.py -v
```
Expected: `ImportError` 或 `ModuleNotFoundError`

- [ ] **Step 3: 创建 `models/category.py`**

```python
# backend/app/modules/repository/models/category.py
import uuid
from typing import Optional
from sqlalchemy import String, Boolean, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.common.entity.base import BaseEntity


class ArchiveCategory(BaseEntity):
    """
    档案门类定义表。
    内置门类（is_builtin=True）对应 DA/T 标准，不可删除。
    自定义门类通过克隆内置门类后在表单设计器中编辑字段 schema。
    """
    __tablename__ = "repo_archive_category"

    code: Mapped[str] = mapped_column(
        String(20), unique=True, nullable=False, comment="门类代码，如 WS/KJ/HJ"
    )
    name: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="门类名称"
    )
    parent_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("repo_archive_category.id", ondelete="SET NULL"),
        nullable=True, comment="父门类（专业档案子门类使用）"
    )
    base_category_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("repo_archive_category.id", ondelete="SET NULL"),
        nullable=True, comment="克隆来源（自定义门类）"
    )
    is_builtin: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false",
        comment="是否内置 DA/T 标准门类"
    )
    requires_privacy_guard: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false",
        comment="是否含个人隐私字段（专业档案）"
    )
    field_schema: Mapped[Optional[dict]] = mapped_column(
        JSON, nullable=True,
        comment="字段定义列表：[{name,label,type,required,options,...}]"
    )
    tenant_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("iam_tenant.id", ondelete="CASCADE"),
        nullable=True, index=True, comment="所属租户（NULL=系统内置）"
    )
```

- [ ] **Step 4: 创建 `models/no_rule.py`（骨架，Plan B 填充）**

```python
# backend/app/modules/repository/models/no_rule.py
import uuid
from typing import Optional
from sqlalchemy import String, Boolean, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.common.entity.base import BaseEntity


class ArchiveNoRule(BaseEntity):
    """
    档号规则配置表。
    rule_template JSONB 存储规则段定义，由 Plan B 的规则引擎解释执行。
    """
    __tablename__ = "repo_archive_no_rule"

    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("repo_archive_category.id", ondelete="CASCADE"),
        nullable=False, index=True, comment="所属门类"
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="规则名称")
    rule_template: Mapped[Optional[dict]] = mapped_column(
        JSON, nullable=True, comment="规则段定义（见 docs/features/feature_档案管理.md 第五章）"
    )
    seq_scope: Mapped[str] = mapped_column(
        String(20), nullable=False, default="catalog_year",
        comment="序号重置范围: catalog | catalog_year | fonds"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true", comment="是否启用"
    )
    tenant_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("iam_tenant.id", ondelete="CASCADE"),
        nullable=True, index=True
    )
```

- [ ] **Step 5: 重写 `models/archive.py`**

```python
# backend/app/modules/repository/models/archive.py
"""
档案库核心数据模型 v2

层级：
  全宗（Fonds，repo_fonds）             ← 保留不变
    └── 目录（Catalog）                  ← 档号编号域，新增
          ├── [一文一件] 件（Archive, level=item）
          └── [案卷卷内] 案卷（Archive, level=volume）
                        └── 卷内文件（Archive, level=item, parent_id=案卷id）

旧表 repo_archive_file / repo_archive_item 保留（不删），待确认后清理。
"""
import uuid
from typing import Optional, List
from sqlalchemy import String, Text, Integer, BigInteger, JSON, ForeignKey, Date, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.common.entity.base import BaseEntity


class Catalog(BaseEntity):
    """目录：全宗下的编号域，案卷号/件号在目录范围内唯一。"""
    __tablename__ = "repo_catalog"

    fonds_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("repo_fonds.id", ondelete="CASCADE"),
        nullable=False, index=True, comment="所属全宗"
    )
    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("repo_archive_category.id", ondelete="RESTRICT"),
        nullable=False, comment="对应门类"
    )
    catalog_no: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="目录号，同全宗内唯一"
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, comment="目录名称")
    year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="年度")
    org_mode: Mapped[str] = mapped_column(
        String(20), nullable=False, default="by_item",
        comment="整理方式: by_item（一文一件）| by_volume（案卷卷内）"
    )
    tenant_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("iam_tenant.id", ondelete="CASCADE"),
        nullable=True, index=True
    )

    archives: Mapped[List["Archive"]] = relationship(
        "Archive", back_populates="catalog",
        primaryjoin="and_(Catalog.id==Archive.catalog_id, Archive.parent_id==None)"
    )


class Archive(BaseEntity):
    """
    档案主表：统一存储件（item）和案卷（volume）。
    level=volume 时为案卷，level=item 且 parent_id=NULL 时为独立件，
    parent_id 有值时为卷内文件。
    """
    __tablename__ = "repo_archive"

    fonds_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("repo_fonds.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    catalog_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("repo_catalog.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    parent_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("repo_archive.id", ondelete="CASCADE"),
        nullable=True, index=True, comment="NULL=顶级，有值=卷内文件"
    )
    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("repo_archive_category.id", ondelete="RESTRICT"),
        nullable=False, index=True
    )
    level: Mapped[str] = mapped_column(
        String(10), nullable=False, comment="volume | item"
    )

    # ── DA/T 必有项（规范化列，全部建索引）──────────────────────────
    archive_no: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, index=True, comment="档号（生成结果，可手动覆盖）"
    )
    fonds_code: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True, comment="全宗号"
    )
    catalog_no: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, comment="目录号"
    )
    volume_no: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, comment="案卷号（一文一件时为空）"
    )
    item_no: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, comment="件号"
    )
    year: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, index=True, comment="年度"
    )
    title: Mapped[str] = mapped_column(
        String(512), nullable=False, index=True, comment="题名"
    )
    creator: Mapped[Optional[str]] = mapped_column(
        String(200), nullable=True, index=True, comment="责任者"
    )
    security_level: Mapped[str] = mapped_column(
        String(20), nullable=False, default="public",
        comment="密级: public | internal | confidential | secret"
    )
    retention_period: Mapped[str] = mapped_column(
        String(20), nullable=False, default="permanent",
        comment="保管期限: permanent | long | short"
    )
    doc_date: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True, comment="文件日期 YYYY-MM-DD"
    )
    pages: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="页数")
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="active",
        comment="active | restricted | destroyed"
    )

    # ── 门类私有字段 ─────────────────────────────────────────────────
    ext_fields: Mapped[Optional[dict]] = mapped_column(
        JSON, nullable=True, comment="门类私有字段（GIN 索引）"
    )

    # ── 存储引用 ──────────────────────────────────────────────────────
    storage_key: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    storage_bucket: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    file_size: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    file_format: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    sha256_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    # ── 系统字段 ──────────────────────────────────────────────────────
    embedding_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending",
        comment="ES/向量化状态: pending | processing | done | failed"
    )
    es_synced_at: Mapped[Optional[str]] = mapped_column(
        String(30), nullable=True, comment="最后成功同步 ES 的时间 ISO8601"
    )
    tenant_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("iam_tenant.id", ondelete="CASCADE"),
        nullable=True, index=True
    )

    # ── 关联 ──────────────────────────────────────────────────────────
    catalog: Mapped["Catalog"] = relationship(
        "Catalog", back_populates="archives",
        foreign_keys=[catalog_id]
    )
    children: Mapped[List["Archive"]] = relationship(
        "Archive", back_populates="parent",
        foreign_keys=[parent_id]
    )
    parent: Mapped[Optional["Archive"]] = relationship(
        "Archive", back_populates="children",
        foreign_keys=[parent_id], remote_side="Archive.id"
    )
```

- [ ] **Step 6: 更新 `models/__init__.py`**

```python
# backend/app/modules/repository/models/__init__.py
from app.modules.repository.models.category import ArchiveCategory
from app.modules.repository.models.no_rule import ArchiveNoRule
from app.modules.repository.models.archive import Catalog, Archive

__all__ = ["ArchiveCategory", "ArchiveNoRule", "Catalog", "Archive"]
```

- [ ] **Step 7: 运行测试，确认通过**

```bash
cd backend && pytest tests/unit/repository/test_models.py -v
```
Expected: 3 个 PASS

- [ ] **Step 8: 创建测试包**

```bash
touch backend/tests/unit/repository/__init__.py
```

- [ ] **Step 9: Commit**

```bash
git add backend/app/modules/repository/models/
git add backend/tests/unit/repository/
git commit -m "feat(archive): add ArchiveCategory, Catalog, Archive ORM models"
```

---

## Task 2：Alembic Migration

**Files:**
- Modify: `backend/alembic/env.py`
- Create: `backend/alembic/versions/2026_04_19_0001_archive_management_foundation.py`

- [ ] **Step 1: 在 `alembic/env.py` 导入新模型**

打开 `backend/alembic/env.py`，找到已有的模型导入区，追加：

```python
# 在已有 import 区域末尾追加
from app.modules.repository.models.category import ArchiveCategory  # noqa: F401
from app.modules.repository.models.no_rule import ArchiveNoRule       # noqa: F401
from app.modules.repository.models.archive import Catalog, Archive    # noqa: F401
```

- [ ] **Step 2: 生成 migration**

```bash
cd backend && alembic revision --autogenerate -m "archive_management_foundation"
```

Expected: 在 `alembic/versions/` 生成新文件，文件名含 `archive_management_foundation`。

- [ ] **Step 3: 检查生成的 migration 文件**

打开生成的文件，确认：
- `upgrade()` 包含 `repo_archive_category`、`repo_catalog`、`repo_archive`、`repo_archive_no_rule` 四张表的 `create_table`
- `downgrade()` 包含对应 `drop_table`（按依赖逆序）
- 旧表 `repo_archive_file`、`repo_archive_item` **不在** `downgrade` 里（保留旧表）

如有问题手动修正。

- [ ] **Step 4: 在 migration 末尾手动追加 GIN 索引**

在生成文件的 `upgrade()` 函数末尾，`create_table` 之后添加：

```python
# GIN 索引（autogenerate 不自动生成，需手动添加）
op.execute("CREATE INDEX IF NOT EXISTS ix_repo_archive_ext_fields_gin ON repo_archive USING GIN (ext_fields)")
op.execute("CREATE INDEX IF NOT EXISTS ix_repo_archive_fonds_catalog_year ON repo_archive (fonds_id, catalog_id, year)")
```

在 `downgrade()` 函数开头添加：

```python
op.execute("DROP INDEX IF EXISTS ix_repo_archive_ext_fields_gin")
op.execute("DROP INDEX IF EXISTS ix_repo_archive_fonds_catalog_year")
```

- [ ] **Step 5: 应用 migration**

```bash
cd backend && alembic upgrade head
```
Expected: 无报错，输出 `Running upgrade ... -> <rev>`

- [ ] **Step 6: 验证表已创建**

```bash
cd backend && python -c "
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from app.core.config import settings

async def check():
    engine = create_async_engine(settings.DATABASE_URL)
    async with engine.connect() as conn:
        result = await conn.exec_driver_sql(
            \"SELECT tablename FROM pg_tables WHERE tablename LIKE 'repo_%' ORDER BY tablename\"
        )
        for row in result:
            print(row[0])
    await engine.dispose()

asyncio.run(check())
"
```
Expected 输出包含：`repo_archive`、`repo_archive_category`、`repo_archive_no_rule`、`repo_catalog`

- [ ] **Step 7: Commit**

```bash
git add backend/alembic/
git commit -m "feat(archive): add migration for archive management foundation tables"
```

---

## Task 3：门类 Schemas + Repository

**Files:**
- Create: `backend/app/modules/repository/schemas/category.py`
- Create: `backend/app/modules/repository/repositories/category_repo.py`

- [ ] **Step 1: 写失败测试**

```python
# backend/tests/unit/repository/test_category_service.py
import uuid
import pytest
from app.modules.repository.schemas.category import CategoryCreate, CategoryRead


def test_category_create_schema_valid():
    data = CategoryCreate(code="TEST", name="测试门类")
    assert data.code == "TEST"
    assert data.is_builtin is False


def test_category_create_schema_requires_code():
    with pytest.raises(Exception):
        CategoryCreate(name="无代码门类")  # code 必填


def test_category_read_schema():
    data = CategoryRead(
        id=uuid.uuid4(),
        code="WS",
        name="文书档案",
        is_builtin=True,
        requires_privacy_guard=False,
        field_schema=None,
    )
    assert data.code == "WS"
```

- [ ] **Step 2: 运行测试，确认失败**

```bash
cd backend && pytest tests/unit/repository/test_category_service.py::test_category_create_schema_valid -v
```
Expected: `ImportError`

- [ ] **Step 3: 创建 `schemas/category.py`**

```python
# backend/app/modules/repository/schemas/category.py
import uuid
from typing import Optional, Any
from pydantic import BaseModel, Field


class FieldDefinition(BaseModel):
    """单个字段的 schema 定义（表单设计器产出）"""
    name: str = Field(..., description="字段 key，存入 ext_fields")
    label: str = Field(..., description="显示标签")
    type: str = Field(..., description="text | number | date | select | boolean | textarea")
    required: bool = False
    placeholder: Optional[str] = None
    validation: Optional[dict[str, Any]] = None
    options: Optional[list[str]] = None
    inherited: bool = Field(default=False, description="从父门类继承，不可删除")


class CategoryCreate(BaseModel):
    code: str = Field(..., max_length=20, description="门类代码")
    name: str = Field(..., max_length=100)
    parent_id: Optional[uuid.UUID] = None
    base_category_id: Optional[uuid.UUID] = Field(
        default=None, description="克隆来源门类 ID"
    )
    requires_privacy_guard: bool = False
    field_schema: Optional[list[FieldDefinition]] = None
    is_builtin: bool = False


class CategoryUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=100)
    requires_privacy_guard: Optional[bool] = None
    field_schema: Optional[list[FieldDefinition]] = None


class CategoryRead(BaseModel):
    id: uuid.UUID
    code: str
    name: str
    parent_id: Optional[uuid.UUID] = None
    base_category_id: Optional[uuid.UUID] = None
    is_builtin: bool
    requires_privacy_guard: bool
    field_schema: Optional[list[FieldDefinition]] = None
    tenant_id: Optional[uuid.UUID] = None

    model_config = {"from_attributes": True}
```

- [ ] **Step 4: 运行测试，确认通过**

```bash
cd backend && pytest tests/unit/repository/test_category_service.py -v
```
Expected: 3 PASS

- [ ] **Step 5: 创建 `repositories/category_repo.py`**

```python
# backend/app/modules/repository/repositories/category_repo.py
import uuid
from typing import Optional
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.repository.models.category import ArchiveCategory


class CategoryRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_by_id(self, category_id: uuid.UUID) -> Optional[ArchiveCategory]:
        result = await self._db.execute(
            select(ArchiveCategory).where(
                and_(ArchiveCategory.id == category_id, ArchiveCategory.is_deleted == False)
            )
        )
        return result.scalar_one_or_none()

    async def get_by_code(self, code: str) -> Optional[ArchiveCategory]:
        result = await self._db.execute(
            select(ArchiveCategory).where(
                and_(ArchiveCategory.code == code, ArchiveCategory.is_deleted == False)
            )
        )
        return result.scalar_one_or_none()

    async def list_all(
        self,
        tenant_id: Optional[uuid.UUID] = None,
        parent_id: Optional[uuid.UUID] = None,
    ) -> list[ArchiveCategory]:
        conditions = [ArchiveCategory.is_deleted == False]
        if tenant_id is not None:
            conditions.append(
                (ArchiveCategory.tenant_id == tenant_id) | (ArchiveCategory.tenant_id == None)
            )
        if parent_id is not None:
            conditions.append(ArchiveCategory.parent_id == parent_id)
        result = await self._db.execute(
            select(ArchiveCategory).where(and_(*conditions))
        )
        return list(result.scalars().all())

    async def create(self, category: ArchiveCategory) -> ArchiveCategory:
        self._db.add(category)
        await self._db.flush()
        await self._db.refresh(category)
        return category

    async def delete(self, category: ArchiveCategory) -> None:
        category.is_deleted = True
        await self._db.flush()
```

- [ ] **Step 6: Commit**

```bash
git add backend/app/modules/repository/schemas/category.py
git add backend/app/modules/repository/repositories/category_repo.py
git commit -m "feat(archive): add CategorySchema and CategoryRepository"
```

---

## Task 4：档案 Schemas + Repository

**Files:**
- Create: `backend/app/modules/repository/schemas/archive.py`
- Create: `backend/app/modules/repository/repositories/archive_repo.py`

- [ ] **Step 1: 写失败测试**

```python
# backend/tests/unit/repository/test_archive_service.py
import uuid
import pytest
from app.modules.repository.schemas.archive import (
    CatalogCreate, CatalogRead, ArchiveCreate, ArchiveRead
)


def test_catalog_create_requires_org_mode():
    cat = CatalogCreate(
        fonds_id=uuid.uuid4(),
        category_id=uuid.uuid4(),
        catalog_no="1",
        name="2024文书目录",
        year=2024,
        org_mode="by_item",
    )
    assert cat.org_mode == "by_item"


def test_catalog_create_invalid_org_mode():
    with pytest.raises(Exception):
        CatalogCreate(
            fonds_id=uuid.uuid4(),
            category_id=uuid.uuid4(),
            catalog_no="1",
            name="X",
            org_mode="invalid_mode",
        )


def test_archive_create_requires_title():
    with pytest.raises(Exception):
        ArchiveCreate(
            fonds_id=uuid.uuid4(),
            catalog_id=uuid.uuid4(),
            category_id=uuid.uuid4(),
            level="item",
            fonds_code="J001",
            # title 缺失
        )
```

- [ ] **Step 2: 运行测试，确认失败**

```bash
cd backend && pytest tests/unit/repository/test_archive_service.py -v
```
Expected: `ImportError`

- [ ] **Step 3: 创建 `schemas/archive.py`**

```python
# backend/app/modules/repository/schemas/archive.py
import uuid
from typing import Optional, Any, Literal
from pydantic import BaseModel, Field


# ── 目录 ──────────────────────────────────────────────────────────────────────

class CatalogCreate(BaseModel):
    fonds_id: uuid.UUID
    category_id: uuid.UUID
    catalog_no: str = Field(..., max_length=50)
    name: str = Field(..., max_length=255)
    year: Optional[int] = None
    org_mode: Literal["by_item", "by_volume"] = "by_item"


class CatalogUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=255)
    year: Optional[int] = None
    org_mode: Optional[Literal["by_item", "by_volume"]] = None


class CatalogRead(BaseModel):
    id: uuid.UUID
    fonds_id: uuid.UUID
    category_id: uuid.UUID
    catalog_no: str
    name: str
    year: Optional[int] = None
    org_mode: str
    tenant_id: Optional[uuid.UUID] = None

    model_config = {"from_attributes": True}


# ── 档案 ──────────────────────────────────────────────────────────────────────

class ArchiveCreate(BaseModel):
    fonds_id: uuid.UUID
    catalog_id: uuid.UUID
    parent_id: Optional[uuid.UUID] = None
    category_id: uuid.UUID
    level: Literal["volume", "item"] = "item"

    # DA/T 必有项
    title: str = Field(..., max_length=512, description="题名（必填）")
    fonds_code: str = Field(..., max_length=50)
    year: Optional[int] = None
    creator: Optional[str] = Field(default=None, max_length=200)
    catalog_no: Optional[str] = Field(default=None, max_length=50)
    volume_no: Optional[str] = Field(default=None, max_length=50)
    item_no: Optional[str] = Field(default=None, max_length=50)
    archive_no: Optional[str] = Field(default=None, max_length=100)
    security_level: Literal["public", "internal", "confidential", "secret"] = "public"
    retention_period: Literal["permanent", "long", "short"] = "permanent"
    doc_date: Optional[str] = None
    pages: Optional[int] = None

    # 门类私有字段
    ext_fields: Optional[dict[str, Any]] = None

    # 存储（可选，归档后再填）
    storage_key: Optional[str] = None
    storage_bucket: Optional[str] = None
    file_size: Optional[int] = None
    file_format: Optional[str] = None
    sha256_hash: Optional[str] = None


class ArchiveUpdate(BaseModel):
    title: Optional[str] = Field(default=None, max_length=512)
    creator: Optional[str] = Field(default=None, max_length=200)
    year: Optional[int] = None
    security_level: Optional[Literal["public", "internal", "confidential", "secret"]] = None
    retention_period: Optional[Literal["permanent", "long", "short"]] = None
    doc_date: Optional[str] = None
    pages: Optional[int] = None
    status: Optional[Literal["active", "restricted", "destroyed"]] = None
    ext_fields: Optional[dict[str, Any]] = None
    archive_no: Optional[str] = Field(default=None, max_length=100)


class ArchiveRead(BaseModel):
    id: uuid.UUID
    fonds_id: uuid.UUID
    catalog_id: uuid.UUID
    parent_id: Optional[uuid.UUID] = None
    category_id: uuid.UUID
    level: str
    archive_no: Optional[str] = None
    fonds_code: str
    catalog_no: Optional[str] = None
    volume_no: Optional[str] = None
    item_no: Optional[str] = None
    year: Optional[int] = None
    title: str
    creator: Optional[str] = None
    security_level: str
    retention_period: str
    doc_date: Optional[str] = None
    pages: Optional[int] = None
    status: str
    ext_fields: Optional[dict[str, Any]] = None
    file_format: Optional[str] = None
    file_size: Optional[int] = None
    embedding_status: str
    tenant_id: Optional[uuid.UUID] = None

    model_config = {"from_attributes": True}


class ArchiveListQuery(BaseModel):
    """档案列表查询参数"""
    fonds_id: Optional[uuid.UUID] = None
    catalog_id: Optional[uuid.UUID] = None
    category_id: Optional[uuid.UUID] = None
    year: Optional[int] = None
    keyword: Optional[str] = Field(default=None, description="题名/责任者关键字")
    security_level: Optional[str] = None
    status: Optional[str] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
```

- [ ] **Step 4: 运行测试，确认通过**

```bash
cd backend && pytest tests/unit/repository/test_archive_service.py -v
```
Expected: 3 PASS

- [ ] **Step 5: 创建 `repositories/archive_repo.py`**

```python
# backend/app/modules/repository/repositories/archive_repo.py
import uuid
from typing import Optional
from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.repository.models.archive import Catalog, Archive
from app.modules.repository.schemas.archive import ArchiveListQuery


class CatalogRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_by_id(self, catalog_id: uuid.UUID) -> Optional[Catalog]:
        result = await self._db.execute(
            select(Catalog).where(
                and_(Catalog.id == catalog_id, Catalog.is_deleted == False)
            )
        )
        return result.scalar_one_or_none()

    async def list_by_fonds(self, fonds_id: uuid.UUID) -> list[Catalog]:
        result = await self._db.execute(
            select(Catalog).where(
                and_(Catalog.fonds_id == fonds_id, Catalog.is_deleted == False)
            )
        )
        return list(result.scalars().all())

    async def create(self, catalog: Catalog) -> Catalog:
        self._db.add(catalog)
        await self._db.flush()
        await self._db.refresh(catalog)
        return catalog

    async def delete(self, catalog: Catalog) -> None:
        catalog.is_deleted = True
        await self._db.flush()


class ArchiveRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_by_id(self, archive_id: uuid.UUID) -> Optional[Archive]:
        result = await self._db.execute(
            select(Archive).where(
                and_(Archive.id == archive_id, Archive.is_deleted == False)
            )
        )
        return result.scalar_one_or_none()

    async def list_with_query(
        self, query: ArchiveListQuery, tenant_id: Optional[uuid.UUID] = None
    ) -> tuple[list[Archive], int]:
        conditions = [Archive.is_deleted == False, Archive.parent_id == None]
        if tenant_id:
            conditions.append(Archive.tenant_id == tenant_id)
        if query.fonds_id:
            conditions.append(Archive.fonds_id == query.fonds_id)
        if query.catalog_id:
            conditions.append(Archive.catalog_id == query.catalog_id)
        if query.category_id:
            conditions.append(Archive.category_id == query.category_id)
        if query.year:
            conditions.append(Archive.year == query.year)
        if query.security_level:
            conditions.append(Archive.security_level == query.security_level)
        if query.status:
            conditions.append(Archive.status == query.status)
        if query.keyword:
            kw = f"%{query.keyword}%"
            conditions.append(or_(Archive.title.ilike(kw), Archive.creator.ilike(kw)))

        count_result = await self._db.execute(
            select(func.count()).select_from(Archive).where(and_(*conditions))
        )
        total = count_result.scalar_one()

        offset = (query.page - 1) * query.page_size
        result = await self._db.execute(
            select(Archive)
            .where(and_(*conditions))
            .order_by(Archive.create_time.desc())
            .offset(offset)
            .limit(query.page_size)
        )
        return list(result.scalars().all()), total

    async def create(self, archive: Archive) -> Archive:
        self._db.add(archive)
        await self._db.flush()
        await self._db.refresh(archive)
        return archive

    async def delete(self, archive: Archive) -> None:
        archive.is_deleted = True
        await self._db.flush()
```

- [ ] **Step 6: Commit**

```bash
git add backend/app/modules/repository/schemas/archive.py
git add backend/app/modules/repository/repositories/archive_repo.py
git commit -m "feat(archive): add Archive/Catalog schemas and repositories"
```

---

## Task 5：Service 层

**Files:**
- Create: `backend/app/modules/repository/services/category_service.py`
- Create: `backend/app/modules/repository/services/archive_service.py`

- [ ] **Step 1: 写失败测试（category service）**

```python
# 追加到 backend/tests/unit/repository/test_category_service.py
import uuid
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock
from app.modules.repository.services.category_service import CategoryService
from app.modules.repository.schemas.category import CategoryCreate
from app.modules.repository.models.category import ArchiveCategory
from app.common.exceptions import BusinessException


@pytest.fixture
def mock_category_repo():
    repo = AsyncMock()
    repo.get_by_code = AsyncMock(return_value=None)
    repo.create = AsyncMock()
    repo.list_all = AsyncMock(return_value=[])
    return repo


@pytest.fixture
def category_service(mock_category_repo):
    service = CategoryService.__new__(CategoryService)
    service._repo = mock_category_repo
    return service


@pytest.mark.asyncio
async def test_create_category_success(category_service, mock_category_repo):
    create_data = CategoryCreate(code="CUSTOM", name="自定义门类")
    mock_category_repo.create.return_value = ArchiveCategory(
        id=uuid.uuid4(), code="CUSTOM", name="自定义门类"
    )
    result = await category_service.create(create_data, tenant_id=uuid.uuid4())
    mock_category_repo.create.assert_called_once()
    assert result.code == "CUSTOM"


@pytest.mark.asyncio
async def test_create_category_duplicate_code_raises(category_service, mock_category_repo):
    mock_category_repo.get_by_code.return_value = ArchiveCategory(
        id=uuid.uuid4(), code="WS", name="文书档案"
    )
    with pytest.raises(BusinessException):
        await category_service.create(
            CategoryCreate(code="WS", name="重复"), tenant_id=uuid.uuid4()
        )


@pytest.mark.asyncio
async def test_delete_builtin_category_raises(category_service, mock_category_repo):
    builtin = ArchiveCategory(id=uuid.uuid4(), code="WS", name="文书档案", is_builtin=True)
    mock_category_repo.get_by_id = AsyncMock(return_value=builtin)
    with pytest.raises(BusinessException):
        await category_service.delete(builtin.id)
```

- [ ] **Step 2: 运行测试，确认失败**

```bash
cd backend && pytest tests/unit/repository/test_category_service.py -k "asyncio" -v
```
Expected: `ImportError` 或 `ModuleNotFoundError`

- [ ] **Step 3: 检查 BusinessException 位置**

```bash
grep -r "class BusinessException" backend/app/
```
如果不存在，在 `backend/app/common/exceptions.py` 追加：
```python
class BusinessException(Exception):
    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message
        super().__init__(message)
```

- [ ] **Step 4: 创建 `services/category_service.py`**

```python
# backend/app/modules/repository/services/category_service.py
import uuid
import copy
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.repository.models.category import ArchiveCategory
from app.modules.repository.repositories.category_repo import CategoryRepository
from app.modules.repository.schemas.category import CategoryCreate, CategoryUpdate, CategoryRead
from app.common.exceptions import BusinessException
from app.common.error_code import ErrorCode


class CategoryService:
    def __init__(self, db: AsyncSession) -> None:
        self._repo = CategoryRepository(db)

    async def create(
        self, data: CategoryCreate, tenant_id: Optional[uuid.UUID]
    ) -> ArchiveCategory:
        existing = await self._repo.get_by_code(data.code)
        if existing:
            raise BusinessException(ErrorCode.VALIDATION_ERROR, f"门类代码 {data.code!r} 已存在")

        category = ArchiveCategory(
            code=data.code,
            name=data.name,
            parent_id=data.parent_id,
            base_category_id=data.base_category_id,
            is_builtin=data.is_builtin,
            requires_privacy_guard=data.requires_privacy_guard,
            field_schema=[f.model_dump() for f in data.field_schema] if data.field_schema else None,
            tenant_id=tenant_id,
        )
        return await self._repo.create(category)

    async def clone(
        self, source_id: uuid.UUID, new_code: str, new_name: str, tenant_id: uuid.UUID
    ) -> ArchiveCategory:
        source = await self._repo.get_by_id(source_id)
        if not source:
            raise BusinessException(ErrorCode.NOT_FOUND, "来源门类不存在")
        existing = await self._repo.get_by_code(new_code)
        if existing:
            raise BusinessException(ErrorCode.VALIDATION_ERROR, f"门类代码 {new_code!r} 已存在")

        cloned_schema = copy.deepcopy(source.field_schema) if source.field_schema else None
        if cloned_schema:
            for field in cloned_schema:
                field["inherited"] = True

        cloned = ArchiveCategory(
            code=new_code,
            name=new_name,
            parent_id=source.parent_id,
            base_category_id=source.id,
            is_builtin=False,
            requires_privacy_guard=source.requires_privacy_guard,
            field_schema=cloned_schema,
            tenant_id=tenant_id,
        )
        return await self._repo.create(cloned)

    async def update(self, category_id: uuid.UUID, data: CategoryUpdate) -> ArchiveCategory:
        category = await self._repo.get_by_id(category_id)
        if not category:
            raise BusinessException(ErrorCode.NOT_FOUND, "门类不存在")
        if data.name is not None:
            category.name = data.name
        if data.requires_privacy_guard is not None:
            category.requires_privacy_guard = data.requires_privacy_guard
        if data.field_schema is not None:
            category.field_schema = [f.model_dump() for f in data.field_schema]
        return category

    async def delete(self, category_id: uuid.UUID) -> None:
        category = await self._repo.get_by_id(category_id)
        if not category:
            raise BusinessException(ErrorCode.NOT_FOUND, "门类不存在")
        if category.is_builtin:
            raise BusinessException(ErrorCode.VALIDATION_ERROR, "内置门类不可删除")
        await self._repo.delete(category)

    async def list_all(
        self, tenant_id: Optional[uuid.UUID] = None, parent_id: Optional[uuid.UUID] = None
    ) -> list[ArchiveCategory]:
        return await self._repo.list_all(tenant_id=tenant_id, parent_id=parent_id)
```

- [ ] **Step 5: 创建 `services/archive_service.py`**

```python
# backend/app/modules/repository/services/archive_service.py
import uuid
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.repository.models.archive import Catalog, Archive
from app.modules.repository.repositories.archive_repo import CatalogRepository, ArchiveRepository
from app.modules.repository.schemas.archive import (
    CatalogCreate, CatalogUpdate,
    ArchiveCreate, ArchiveUpdate, ArchiveListQuery
)
from app.common.exceptions import BusinessException
from app.common.error_code import ErrorCode


class CatalogService:
    def __init__(self, db: AsyncSession) -> None:
        self._repo = CatalogRepository(db)

    async def create(self, data: CatalogCreate, tenant_id: Optional[uuid.UUID]) -> Catalog:
        catalog = Catalog(
            fonds_id=data.fonds_id,
            category_id=data.category_id,
            catalog_no=data.catalog_no,
            name=data.name,
            year=data.year,
            org_mode=data.org_mode,
            tenant_id=tenant_id,
        )
        return await self._repo.create(catalog)

    async def list_by_fonds(self, fonds_id: uuid.UUID) -> list[Catalog]:
        return await self._repo.list_by_fonds(fonds_id)

    async def delete(self, catalog_id: uuid.UUID) -> None:
        catalog = await self._repo.get_by_id(catalog_id)
        if not catalog:
            raise BusinessException(ErrorCode.NOT_FOUND, "目录不存在")
        await self._repo.delete(catalog)


class ArchiveService:
    def __init__(self, db: AsyncSession) -> None:
        self._repo = ArchiveRepository(db)

    async def create(self, data: ArchiveCreate, tenant_id: Optional[uuid.UUID]) -> Archive:
        archive = Archive(
            fonds_id=data.fonds_id,
            catalog_id=data.catalog_id,
            parent_id=data.parent_id,
            category_id=data.category_id,
            level=data.level,
            title=data.title,
            fonds_code=data.fonds_code,
            year=data.year,
            creator=data.creator,
            catalog_no=data.catalog_no,
            volume_no=data.volume_no,
            item_no=data.item_no,
            archive_no=data.archive_no,
            security_level=data.security_level,
            retention_period=data.retention_period,
            doc_date=data.doc_date,
            pages=data.pages,
            ext_fields=data.ext_fields,
            storage_key=data.storage_key,
            storage_bucket=data.storage_bucket,
            file_size=data.file_size,
            file_format=data.file_format,
            sha256_hash=data.sha256_hash,
            tenant_id=tenant_id,
        )
        return await self._repo.create(archive)

    async def get(self, archive_id: uuid.UUID) -> Archive:
        archive = await self._repo.get_by_id(archive_id)
        if not archive:
            raise BusinessException(ErrorCode.NOT_FOUND, "档案不存在")
        return archive

    async def update(self, archive_id: uuid.UUID, data: ArchiveUpdate) -> Archive:
        archive = await self._repo.get_by_id(archive_id)
        if not archive:
            raise BusinessException(ErrorCode.NOT_FOUND, "档案不存在")
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(archive, field, value)
        return archive

    async def delete(self, archive_id: uuid.UUID) -> None:
        archive = await self._repo.get_by_id(archive_id)
        if not archive:
            raise BusinessException(ErrorCode.NOT_FOUND, "档案不存在")
        await self._repo.delete(archive)

    async def list_archives(
        self, query: ArchiveListQuery, tenant_id: Optional[uuid.UUID] = None
    ) -> tuple[list[Archive], int]:
        return await self._repo.list_with_query(query, tenant_id=tenant_id)
```

- [ ] **Step 6: 运行全部测试**

```bash
cd backend && pytest tests/unit/repository/ -v
```
Expected: 全部 PASS（至少 6 个）

- [ ] **Step 7: Commit**

```bash
git add backend/app/modules/repository/services/
git commit -m "feat(archive): add CategoryService and ArchiveService"
```

---

## Task 6：API 路由

**Files:**
- Create: `backend/app/modules/repository/api/routes_category.py`
- Create: `backend/app/modules/repository/api/routes_archive.py`
- Modify: `backend/app/api/v1/router.py`

- [ ] **Step 1: 创建 `api/routes_category.py`**

```python
# backend/app/modules/repository/api/routes_category.py
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.infra.db.session import get_db
from app.modules.iam.api.dependencies import get_current_user
from app.modules.iam.models.user import User
from app.modules.repository.services.category_service import CategoryService
from app.modules.repository.schemas.category import CategoryCreate, CategoryUpdate, CategoryRead
from app.common.response import success, ResponseModel

router = APIRouter(prefix="/archive/categories", tags=["档案门类"])


@router.get("", response_model=ResponseModel[list[CategoryRead]])
async def list_categories(
    parent_id: Optional[uuid.UUID] = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = CategoryService(db)
    items = await svc.list_all(tenant_id=current_user.tenant_id, parent_id=parent_id)
    return success([CategoryRead.model_validate(i) for i in items])


@router.post("", response_model=ResponseModel[CategoryRead])
async def create_category(
    data: CategoryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = CategoryService(db)
    item = await svc.create(data, tenant_id=current_user.tenant_id)
    await db.commit()
    return success(CategoryRead.model_validate(item))


@router.post("/{category_id}/clone", response_model=ResponseModel[CategoryRead])
async def clone_category(
    category_id: uuid.UUID,
    new_code: str = Query(...),
    new_name: str = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = CategoryService(db)
    item = await svc.clone(category_id, new_code, new_name, tenant_id=current_user.tenant_id)
    await db.commit()
    return success(CategoryRead.model_validate(item))


@router.put("/{category_id}", response_model=ResponseModel[CategoryRead])
async def update_category(
    category_id: uuid.UUID,
    data: CategoryUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = CategoryService(db)
    item = await svc.update(category_id, data)
    await db.commit()
    return success(CategoryRead.model_validate(item))


@router.delete("/{category_id}", response_model=ResponseModel[None])
async def delete_category(
    category_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = CategoryService(db)
    await svc.delete(category_id)
    await db.commit()
    return success()
```

- [ ] **Step 2: 创建 `api/routes_archive.py`**

```python
# backend/app/modules/repository/api/routes_archive.py
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Query, Body
from sqlalchemy.ext.asyncio import AsyncSession
from app.infra.db.session import get_db
from app.modules.iam.api.dependencies import get_current_user
from app.modules.iam.models.user import User
from app.modules.repository.services.archive_service import CatalogService, ArchiveService
from app.modules.repository.schemas.archive import (
    CatalogCreate, CatalogRead,
    ArchiveCreate, ArchiveUpdate, ArchiveRead, ArchiveListQuery,
)
from app.common.response import success, ResponseModel

router = APIRouter(tags=["档案管理"])


# ── 目录 ──────────────────────────────────────────────────────────────────────

@router.get("/archive/catalogs", response_model=ResponseModel[list[CatalogRead]])
async def list_catalogs(
    fonds_id: uuid.UUID = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = CatalogService(db)
    items = await svc.list_by_fonds(fonds_id)
    return success([CatalogRead.model_validate(i) for i in items])


@router.post("/archive/catalogs", response_model=ResponseModel[CatalogRead])
async def create_catalog(
    data: CatalogCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = CatalogService(db)
    item = await svc.create(data, tenant_id=current_user.tenant_id)
    await db.commit()
    return success(CatalogRead.model_validate(item))


@router.delete("/archive/catalogs/{catalog_id}", response_model=ResponseModel[None])
async def delete_catalog(
    catalog_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = CatalogService(db)
    await svc.delete(catalog_id)
    await db.commit()
    return success()


# ── 档案 ──────────────────────────────────────────────────────────────────────

@router.get("/archive/records", response_model=ResponseModel[dict])
async def list_archives(
    fonds_id: Optional[uuid.UUID] = Query(default=None),
    catalog_id: Optional[uuid.UUID] = Query(default=None),
    category_id: Optional[uuid.UUID] = Query(default=None),
    year: Optional[int] = Query(default=None),
    keyword: Optional[str] = Query(default=None),
    security_level: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = ArchiveListQuery(
        fonds_id=fonds_id, catalog_id=catalog_id, category_id=category_id,
        year=year, keyword=keyword, security_level=security_level,
        status=status, page=page, page_size=page_size,
    )
    svc = ArchiveService(db)
    items, total = await svc.list_archives(query, tenant_id=current_user.tenant_id)
    return success({
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [ArchiveRead.model_validate(i) for i in items],
    })


@router.post("/archive/records", response_model=ResponseModel[ArchiveRead])
async def create_archive(
    data: ArchiveCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = ArchiveService(db)
    item = await svc.create(data, tenant_id=current_user.tenant_id)
    await db.commit()
    return success(ArchiveRead.model_validate(item))


@router.get("/archive/records/{archive_id}", response_model=ResponseModel[ArchiveRead])
async def get_archive(
    archive_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = ArchiveService(db)
    item = await svc.get(archive_id)
    return success(ArchiveRead.model_validate(item))


@router.put("/archive/records/{archive_id}", response_model=ResponseModel[ArchiveRead])
async def update_archive(
    archive_id: uuid.UUID,
    data: ArchiveUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = ArchiveService(db)
    item = await svc.update(archive_id, data)
    await db.commit()
    return success(ArchiveRead.model_validate(item))


@router.delete("/archive/records/{archive_id}", response_model=ResponseModel[None])
async def delete_archive(
    archive_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = ArchiveService(db)
    await svc.delete(archive_id)
    await db.commit()
    return success()


@router.patch("/archive/records/{archive_id}/override-no", response_model=ResponseModel[ArchiveRead])
async def override_archive_no(
    archive_id: uuid.UUID,
    archive_no: str = Body(..., embed=True),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """手动覆盖档号（操作写入审计日志由 AuditMixin 自动处理）"""
    svc = ArchiveService(db)
    item = await svc.update(archive_id, ArchiveUpdate(archive_no=archive_no))
    await db.commit()
    return success(ArchiveRead.model_validate(item))
```

- [ ] **Step 3: 挂载路由到 `router.py`**

打开 `backend/app/api/v1/router.py`，在已有路由导入末尾追加：

```python
from app.modules.repository.api.routes_category import router as archive_category_router
from app.modules.repository.api.routes_archive import router as archive_router

# 在 router.include_router 调用区追加：
router.include_router(archive_category_router)
router.include_router(archive_router)
```

- [ ] **Step 4: 启动后端，验证路由已注册**

```bash
cd backend && python app/main.py &
sleep 3
curl -s http://localhost:8000/api/v1/archive/categories | python -m json.tool | head -5
# Expected: {"code": ...}  (401 或 200 均可，关键是路由存在不报 404)
```

- [ ] **Step 5: 运行全部测试**

```bash
cd backend && pytest tests/unit/repository/ -v
```
Expected: 全部 PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/modules/repository/api/
git add backend/app/api/v1/router.py
git commit -m "feat(archive): add archive category and records CRUD API routes"
```

---

## Task 7：内置门类种子数据

**Files:**
- Modify: `backend/app/scripts/seed.py`（或新建 `backend/app/scripts/seed_archive_categories.py`）

- [ ] **Step 1: 确认种子脚本位置**

```bash
ls backend/app/scripts/
```

- [ ] **Step 2: 创建 `seed_archive_categories.py`**

```python
# backend/app/scripts/seed_archive_categories.py
"""
初始化内置档案门类（DA/T 标准 + 专业档案）。
幂等：已存在的 code 跳过，不重复插入。
运行：cd backend && python -m app.scripts.seed_archive_categories
"""
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import select
from app.core.config import settings
from app.modules.repository.models.category import ArchiveCategory

BUILTIN_CATEGORIES = [
    {"code": "WS", "name": "文书档案",  "requires_privacy_guard": False, "parent_id_code": None,
     "field_schema": [
         {"name": "doc_no",    "label": "文号",    "type": "text",   "required": False, "inherited": False},
         {"name": "doc_type",  "label": "文件类型", "type": "select", "required": False,
          "options": ["通知", "请示", "报告", "批复", "决定", "会议纪要", "其他"], "inherited": False},
     ]},
    {"code": "KJ", "name": "科技档案",  "requires_privacy_guard": False, "parent_id_code": None,
     "field_schema": [
         {"name": "project_code", "label": "项目编号", "type": "text", "required": False, "inherited": False},
         {"name": "drawing_type", "label": "图纸类别", "type": "select", "required": False,
          "options": ["施工图", "竣工图", "草图", "设计图"], "inherited": False},
         {"name": "version",      "label": "版本号",   "type": "text", "required": False, "inherited": False},
     ]},
    {"code": "HJ", "name": "会计档案",  "requires_privacy_guard": False, "parent_id_code": None,
     "field_schema": [
         {"name": "voucher_type", "label": "凭证类型", "type": "select", "required": False,
          "options": ["记账凭证", "银行凭证", "报销凭证"], "inherited": False},
         {"name": "account_period", "label": "会计期间", "type": "text", "required": False, "inherited": False},
     ]},
    {"code": "ZP", "name": "照片档案",  "requires_privacy_guard": False, "parent_id_code": None,
     "field_schema": [
         {"name": "photo_subject", "label": "摄影主题", "type": "text",   "required": False, "inherited": False},
         {"name": "photographer",  "label": "摄影者",   "type": "text",   "required": False, "inherited": False},
         {"name": "shoot_location","label": "拍摄地点", "type": "text",   "required": False, "inherited": False},
     ]},
    {"code": "SX", "name": "声像档案",  "requires_privacy_guard": False, "parent_id_code": None,
     "field_schema": [
         {"name": "media_type",    "label": "媒体类型", "type": "select", "required": False,
          "options": ["音频", "视频"], "inherited": False},
         {"name": "duration_sec",  "label": "时长(秒)", "type": "number", "required": False, "inherited": False},
     ]},
    {"code": "DZ", "name": "电子档案",  "requires_privacy_guard": False, "parent_id_code": None, "field_schema": []},
    {"code": "SW", "name": "实物档案",  "requires_privacy_guard": False, "parent_id_code": None,
     "field_schema": [
         {"name": "material",    "label": "材质",   "type": "text", "required": False, "inherited": False},
         {"name": "dimensions",  "label": "尺寸",   "type": "text", "required": False, "inherited": False},
         {"name": "quantity",    "label": "数量",   "type": "number","required": False, "inherited": False},
     ]},
    # 专业档案父类
    {"code": "ZY", "name": "专业档案",  "requires_privacy_guard": False, "parent_id_code": None, "field_schema": []},
    # 专业档案子类
    {"code": "ZY_HY", "name": "婚姻档案",      "requires_privacy_guard": True, "parent_id_code": "ZY",
     "field_schema": [
         {"name": "party_a_name",   "label": "当事人甲姓名", "type": "text",   "required": True,  "inherited": False},
         {"name": "party_a_id",     "label": "当事人甲证件号","type": "text",  "required": True,  "inherited": False},
         {"name": "party_b_name",   "label": "当事人乙姓名", "type": "text",   "required": True,  "inherited": False},
         {"name": "party_b_id",     "label": "当事人乙证件号","type": "text",  "required": True,  "inherited": False},
         {"name": "marriage_status","label": "婚姻状态",     "type": "select", "required": True,
          "options": ["结婚", "离婚"], "inherited": False},
         {"name": "reg_authority",  "label": "登记机关",     "type": "text",   "required": False, "inherited": False},
     ]},
    {"code": "ZY_FP", "name": "扶贫档案",      "requires_privacy_guard": True, "parent_id_code": "ZY",
     "field_schema": [
         {"name": "household_head", "label": "户主姓名",   "type": "text",   "required": True,  "inherited": False},
         {"name": "head_id",        "label": "户主证件号", "type": "text",   "required": True,  "inherited": False},
         {"name": "poverty_reason", "label": "致贫原因",   "type": "select", "required": False,
          "options": ["因病", "因残", "因学", "因灾", "缺劳力", "缺技术", "其他"], "inherited": False},
         {"name": "exit_time",      "label": "退出时间",   "type": "date",   "required": False, "inherited": False},
     ]},
    {"code": "ZY_TQ", "name": "土地确权档案",  "requires_privacy_guard": True, "parent_id_code": "ZY",
     "field_schema": [
         {"name": "owner_name",  "label": "权利人姓名", "type": "text",   "required": True,  "inherited": False},
         {"name": "owner_id",    "label": "证件号",     "type": "text",   "required": True,  "inherited": False},
         {"name": "parcel_no",   "label": "地块编号",   "type": "text",   "required": True,  "inherited": False},
         {"name": "area_mu",     "label": "面积(亩)",   "type": "number", "required": False, "inherited": False},
         {"name": "cert_date",   "label": "发证日期",   "type": "date",   "required": False, "inherited": False},
     ]},
    {"code": "ZY_SC", "name": "出生医疗证明",  "requires_privacy_guard": True, "parent_id_code": "ZY",
     "field_schema": [
         {"name": "newborn_name",  "label": "新生儿姓名", "type": "text", "required": True,  "inherited": False},
         {"name": "birth_date",    "label": "出生日期",   "type": "date", "required": True,  "inherited": False},
         {"name": "mother_name",   "label": "母亲姓名",   "type": "text", "required": True,  "inherited": False},
         {"name": "mother_id",     "label": "母亲证件号", "type": "text", "required": True,  "inherited": False},
         {"name": "hospital",      "label": "接生机构",   "type": "text", "required": False, "inherited": False},
         {"name": "cert_no",       "label": "证件编号",   "type": "text", "required": False, "inherited": False},
     ]},
    {"code": "ZY_TY", "name": "退役军人档案",  "requires_privacy_guard": True, "parent_id_code": "ZY",
     "field_schema": [
         {"name": "veteran_name",  "label": "姓名",     "type": "text",   "required": True,  "inherited": False},
         {"name": "veteran_id",    "label": "证件号",   "type": "text",   "required": True,  "inherited": False},
         {"name": "service_years", "label": "服役年限", "type": "number", "required": False, "inherited": False},
         {"name": "troop_no",      "label": "部队番号", "type": "text",   "required": False, "inherited": False},
         {"name": "retire_type",   "label": "退役类型", "type": "select", "required": False,
          "options": ["安置", "自主就业", "退休"], "inherited": False},
     ]},
    {"code": "ZY_DB", "name": "低保档案",      "requires_privacy_guard": True, "parent_id_code": "ZY",
     "field_schema": [
         {"name": "household_head", "label": "户主姓名",   "type": "text",   "required": True,  "inherited": False},
         {"name": "family_members", "label": "家庭人口",   "type": "number", "required": False, "inherited": False},
         {"name": "subsidy_type",   "label": "低保类别",   "type": "select", "required": False,
          "options": ["城市低保", "农村低保"], "inherited": False},
         {"name": "approve_org",    "label": "审批机关",   "type": "text",   "required": False, "inherited": False},
         {"name": "start_date",     "label": "起始日期",   "type": "date",   "required": False, "inherited": False},
     ]},
]


async def seed(db: AsyncSession) -> None:
    code_to_id: dict[str, object] = {}

    # 第一轮：插入所有非子类（parent_id_code=None 的先插）
    for item in BUILTIN_CATEGORIES:
        if item["parent_id_code"] is not None:
            continue
        result = await db.execute(
            select(ArchiveCategory).where(ArchiveCategory.code == item["code"])
        )
        existing = result.scalar_one_or_none()
        if existing:
            code_to_id[item["code"]] = existing.id
            print(f"  skip existing: {item['code']}")
            continue
        cat = ArchiveCategory(
            code=item["code"],
            name=item["name"],
            is_builtin=True,
            requires_privacy_guard=item["requires_privacy_guard"],
            field_schema=item["field_schema"] or None,
        )
        db.add(cat)
        await db.flush()
        code_to_id[item["code"]] = cat.id
        print(f"  inserted: {item['code']} {item['name']}")

    # 第二轮：插入子类
    for item in BUILTIN_CATEGORIES:
        if item["parent_id_code"] is None:
            continue
        result = await db.execute(
            select(ArchiveCategory).where(ArchiveCategory.code == item["code"])
        )
        existing = result.scalar_one_or_none()
        if existing:
            print(f"  skip existing: {item['code']}")
            continue
        cat = ArchiveCategory(
            code=item["code"],
            name=item["name"],
            is_builtin=True,
            requires_privacy_guard=item["requires_privacy_guard"],
            parent_id=code_to_id.get(item["parent_id_code"]),
            field_schema=item["field_schema"] or None,
        )
        db.add(cat)
        await db.flush()
        print(f"  inserted: {item['code']} {item['name']}")

    await db.commit()
    print("Done.")


async def main() -> None:
    engine = create_async_engine(settings.DATABASE_URL)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as db:
        await seed(db)
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 3: 运行种子脚本**

```bash
cd backend && python -m app.scripts.seed_archive_categories
```
Expected: 输出 15 行 `inserted: XX XXXX`（或 skip 如已存在）

- [ ] **Step 4: 验证**

```bash
cd backend && python -c "
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import select, func
from app.core.config import settings
from app.modules.repository.models.category import ArchiveCategory

async def check():
    engine = create_async_engine(settings.DATABASE_URL)
    async with async_sessionmaker(engine)() as db:
        result = await db.execute(select(func.count()).select_from(ArchiveCategory))
        print(f'Total categories: {result.scalar()}')
    await engine.dispose()

asyncio.run(check())
"
```
Expected: `Total categories: 15`

- [ ] **Step 5: Commit**

```bash
git add backend/app/scripts/seed_archive_categories.py
git commit -m "feat(archive): add builtin archive category seed data (DA/T + 专业档案)"
```

---

## 自查结果

**Spec coverage:**

| Spec 章节 | 对应 Task |
|------|------|
| 四、数据库设计（7张表中的5张） | Task 1, 2 |
| 三、档案门类体系（内置+专业档案） | Task 7 |
| 九、API 结构（category/catalog/records） | Task 6 |
| 八、可视化表单设计器（field_schema 结构） | Task 3 schemas |
| 七、ES 同步 | Plan D（独立计划） |
| 五、档号规则引擎 | Plan B（独立计划） |
| 六、批量导入流程 | Plan C（独立计划） |

`repo_import_task` 和 `repo_field_mapping_template` 的模型在 Plan C 创建，Plan A 专注基础数据层。

**Placeholder 扫描:** 无 TBD/TODO。

**类型一致性:** `ArchiveCategory`、`Catalog`、`Archive` 在所有 Task 中命名一致；`CategoryService` / `ArchiveService` 签名前后一致。
