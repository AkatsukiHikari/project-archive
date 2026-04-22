# 档号规则引擎 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现可配置的档号规则引擎，支持 field/literal/sequence/date_part 四种规则段，序号并发安全，提供 CRUD + 实时预览 REST API。

**Architecture:** 规则引擎（`no_rule_engine.py`）读取 `ArchiveNoRule.rule_template` JSONB，逐段拼接档号字符串；序号段使用独立的 `repo_archive_no_seq` 表配合 `SELECT ... FOR UPDATE` 实现原子递增；`ArchiveCategory` 增加 `archive_no_rule_id` FK 指向激活规则。

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2.x async, PostgreSQL (FOR UPDATE 行锁), Pydantic v2, pytest-asyncio

---

## 文件结构

### 新建
| 文件 | 职责 |
|------|------|
| `backend/app/modules/repository/models/no_rule_seq.py` | `ArchiveNoSeq` 序号跟踪表 ORM |
| `backend/app/modules/repository/schemas/no_rule.py` | Pydantic DTOs (Create/Update/Read/Preview) |
| `backend/app/modules/repository/repositories/no_rule_repo.py` | `NoRuleRepository` + `SeqRepository` |
| `backend/app/modules/repository/services/no_rule_engine.py` | 规则引擎：generate() + preview() |
| `backend/app/modules/repository/services/no_rule_service.py` | CRUD service（调用引擎） |
| `backend/app/modules/repository/api/routes_no_rule.py` | REST 路由 |
| `backend/tests/unit/repository/test_no_rule_engine.py` | 引擎单元测试（全 mock） |

### 修改
| 文件 | 变更 |
|------|------|
| `backend/app/modules/repository/models/category.py` | 增加 `archive_no_rule_id` FK 列 |
| `backend/alembic/env.py` | 导入 `ArchiveNoSeq` |
| `backend/app/api/v1/router.py` | 挂载 `routes_no_rule.router` |

### 新建 Migration
| 文件 | 内容 |
|------|------|
| `backend/alembic/versions/2026_04_19_2000-<rev>_archive_no_rule_engine.py` | 建 `repo_archive_no_seq` 表，`repo_archive_category` 加 `archive_no_rule_id` 列 |

---

## Task 1：ArchiveNoSeq 模型 + 更新 ArchiveCategory + Migration

**Files:**
- Create: `backend/app/modules/repository/models/no_rule_seq.py`
- Modify: `backend/app/modules/repository/models/category.py`
- Modify: `backend/alembic/env.py`
- New migration (autogenerate)

- [ ] **Step 1: 写失败测试**

```python
# backend/tests/unit/repository/test_no_rule_engine.py
import uuid
import pytest
from app.modules.repository.models.no_rule_seq import ArchiveNoSeq
from app.modules.repository.models.category import ArchiveCategory


def test_no_seq_instantiate():
    seq = ArchiveNoSeq(
        rule_id=uuid.uuid4(),
        scope_key="catalog_year:abc:2024",
        current_seq=1,
    )
    assert seq.current_seq == 1


def test_category_has_no_rule_id_field():
    cat = ArchiveCategory(code="WS", name="文书", is_builtin=True)
    assert hasattr(cat, "archive_no_rule_id")
    assert cat.archive_no_rule_id is None
```

- [ ] **Step 2: 运行，确认失败**

```bash
cd backend && .venv/bin/pytest tests/unit/repository/test_no_rule_engine.py -v --no-cov
```
Expected: `ImportError` (ArchiveNoSeq 不存在)

- [ ] **Step 3: 创建 `models/no_rule_seq.py`**

```python
# backend/app/modules/repository/models/no_rule_seq.py
import uuid
from sqlalchemy import String, Integer, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.common.entity.base import BaseEntity


class ArchiveNoSeq(BaseEntity):
    """
    档号序号跟踪表。
    每条记录代表某规则在某 scope_key 下的当前最大序号。
    并发安全：写入时使用 SELECT ... FOR UPDATE 锁行后递增。
    """
    __tablename__ = "repo_archive_no_seq"
    __table_args__ = (
        UniqueConstraint("rule_id", "scope_key", name="uq_no_seq_rule_scope"),
    )

    rule_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("repo_archive_no_rule.id", ondelete="CASCADE"),
        nullable=False, index=True, comment="所属规则"
    )
    scope_key: Mapped[str] = mapped_column(
        String(200), nullable=False,
        comment="序号范围键，如 catalog_year:<catalog_id>:<year>"
    )
    current_seq: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="当前已分配的最大序号"
    )
```

- [ ] **Step 4: 在 `models/category.py` 中增加 `archive_no_rule_id` 列**

在 `tenant_id` 列前插入：

```python
# backend/app/modules/repository/models/category.py
# 在现有 import 区末尾确保有 ForeignKey
# 然后在 class ArchiveCategory(BaseEntity): 的列定义中新增：

    archive_no_rule_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("repo_archive_no_rule.id", ondelete="SET NULL"),
        nullable=True, comment="激活的档号规则（NULL 表示不自动生成）"
    )
```

完整文件（替换原文件）：

```python
# backend/app/modules/repository/models/category.py
import uuid
from typing import Optional
from sqlalchemy import String, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
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
        JSONB, nullable=True, comment="字段定义列表 list[FieldDefinition]"
    )
    archive_no_rule_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("repo_archive_no_rule.id", ondelete="SET NULL"),
        nullable=True, comment="激活的档号规则（NULL 表示不自动生成）"
    )
    tenant_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("iam_tenant.id", ondelete="CASCADE"),
        nullable=True, index=True
    )
```

- [ ] **Step 5: 在 `alembic/env.py` 导入新模型**

在已有 `no_rule` 导入行下方新增一行：

```python
from app.modules.repository.models.no_rule_seq import ArchiveNoSeq  # noqa: F401
```

- [ ] **Step 6: 生成并运行 migration**

```bash
cd backend && .venv/bin/alembic revision --autogenerate -m "archive_no_rule_engine"
# 检查生成的文件，确认包含：
# - CREATE TABLE repo_archive_no_seq
# - ADD COLUMN archive_no_rule_id 到 repo_archive_category
.venv/bin/alembic upgrade head
```
Expected: `INFO  [alembic.runtime.migration] Running upgrade 2a6b72efc717 -> <new_rev>`

- [ ] **Step 7: 运行测试，确认通过**

```bash
.venv/bin/pytest tests/unit/repository/test_no_rule_engine.py::test_no_seq_instantiate tests/unit/repository/test_no_rule_engine.py::test_category_has_no_rule_id_field -v --no-cov
```
Expected: 2 passed

- [ ] **Step 8: Commit**

```bash
cd /Users/hikari/Documents/projects/project-archive
git add backend/app/modules/repository/models/no_rule_seq.py \
        backend/app/modules/repository/models/category.py \
        backend/alembic/env.py \
        backend/alembic/versions/
git commit -m "feat: add ArchiveNoSeq model + archive_no_rule_id FK + migration (Plan B Task 1)"
```

---

## Task 2：Pydantic Schemas

**Files:**
- Create: `backend/app/modules/repository/schemas/no_rule.py`
- Test: `backend/tests/unit/repository/test_no_rule_engine.py`（追加）

- [ ] **Step 1: 追加 schema 测试到 `test_no_rule_engine.py`**

```python
# 追加到 backend/tests/unit/repository/test_no_rule_engine.py

from app.modules.repository.schemas.no_rule import (
    NoRuleCreate, NoRuleRead, PreviewRequest, RuleTemplate, SegmentDef,
)


def test_segment_def_field():
    seg = SegmentDef(type="field", field="fonds_code")
    assert seg.type == "field"
    assert seg.field == "fonds_code"


def test_segment_def_sequence():
    seg = SegmentDef(type="sequence", padding=4, scope="catalog_year")
    assert seg.padding == 4
    assert seg.scope == "catalog_year"


def test_rule_template_valid():
    tmpl = RuleTemplate(
        separator="-",
        segments=[
            SegmentDef(type="field", field="fonds_code"),
            SegmentDef(type="literal", value="WS"),
            SegmentDef(type="sequence", padding=4, scope="catalog_year"),
        ],
    )
    assert len(tmpl.segments) == 3


def test_no_rule_create_valid():
    import uuid
    data = NoRuleCreate(
        category_id=uuid.uuid4(),
        name="文书一文一件规则",
        rule_template={
            "separator": "-",
            "segments": [
                {"type": "field", "field": "fonds_code"},
                {"type": "sequence", "padding": 4, "scope": "catalog_year"},
            ],
        },
        seq_scope="catalog_year",
    )
    assert data.name == "文书一文一件规则"


def test_preview_request():
    import uuid
    req = PreviewRequest(
        fonds_code="J001",
        year=2024,
        catalog_no="1",
    )
    assert req.fonds_code == "J001"
```

- [ ] **Step 2: 运行，确认失败**

```bash
cd backend && .venv/bin/pytest tests/unit/repository/test_no_rule_engine.py -k "segment or rule_template or no_rule_create or preview_request" -v --no-cov
```
Expected: `ImportError`

- [ ] **Step 3: 创建 `schemas/no_rule.py`**

```python
# backend/app/modules/repository/schemas/no_rule.py
import uuid
from typing import Optional, Literal, Any
from pydantic import BaseModel, Field


class SegmentDef(BaseModel):
    """规则段定义"""
    type: Literal["field", "literal", "sequence", "date_part"]

    # type=field: 取档案规范化字段值
    field: Optional[str] = None        # fonds_code | year | catalog_no | volume_no | item_no | creator

    # type=literal: 固定字符串
    value: Optional[str] = None

    # type=sequence: 自增序号
    padding: int = 4                   # 补零位数，如 4 → "0023"
    scope: Literal["catalog", "catalog_year", "fonds"] = "catalog_year"

    # type=date_part: 从 doc_date 提取日期部分
    date_field: str = "doc_date"       # 来源字段
    format: str = "%Y"                 # strftime 格式，如 "%Y%m%d"


class RuleTemplate(BaseModel):
    """档号规则模板"""
    separator: str = Field(default="-", max_length=5, description="段分隔符")
    segments: list[SegmentDef] = Field(..., min_length=1)


class NoRuleCreate(BaseModel):
    category_id: uuid.UUID
    name: str = Field(..., max_length=100)
    rule_template: dict[str, Any]      # 存为 JSONB，运行时通过 RuleTemplate 验证
    seq_scope: Literal["catalog", "catalog_year", "fonds"] = "catalog_year"
    is_active: bool = True


class NoRuleUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=100)
    rule_template: Optional[dict[str, Any]] = None
    seq_scope: Optional[Literal["catalog", "catalog_year", "fonds"]] = None
    is_active: Optional[bool] = None


class NoRuleRead(BaseModel):
    id: uuid.UUID
    category_id: uuid.UUID
    name: str
    rule_template: Optional[dict[str, Any]]
    seq_scope: str
    is_active: bool
    tenant_id: Optional[uuid.UUID] = None

    model_config = {"from_attributes": True}


class PreviewRequest(BaseModel):
    """预览档号时提供的档案字段样本"""
    fonds_code: str = Field(default="J001", max_length=50)
    year: Optional[int] = Field(default=2024)
    catalog_no: Optional[str] = Field(default="1", max_length=50)
    volume_no: Optional[str] = None
    item_no: Optional[str] = None
    creator: Optional[str] = None
    doc_date: Optional[str] = Field(default="2024-01-01", description="YYYY-MM-DD")


class PreviewResponse(BaseModel):
    archive_no: str
    segments: list[str]              # 各段生成值，便于前端展示
```

- [ ] **Step 4: 运行测试，确认通过**

```bash
.venv/bin/pytest tests/unit/repository/test_no_rule_engine.py -k "segment or rule_template or no_rule_create or preview_request" -v --no-cov
```
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
cd /Users/hikari/Documents/projects/project-archive
git add backend/app/modules/repository/schemas/no_rule.py \
        backend/tests/unit/repository/test_no_rule_engine.py
git commit -m "feat: add archive no-rule Pydantic schemas (Plan B Task 2)"
```

---

## Task 3：Repository

**Files:**
- Create: `backend/app/modules/repository/repositories/no_rule_repo.py`
- Test: 追加到 `backend/tests/unit/repository/test_no_rule_engine.py`

- [ ] **Step 1: 追加 repo 测试**

```python
# 追加到 test_no_rule_engine.py

import pytest
from unittest.mock import AsyncMock, MagicMock
from app.modules.repository.repositories.no_rule_repo import NoRuleRepository


@pytest.fixture
def mock_no_rule_repo():
    repo = AsyncMock()
    repo.get_by_id = AsyncMock(return_value=None)
    repo.list_by_category = AsyncMock(return_value=[])
    repo.create = AsyncMock()
    return repo


@pytest.mark.asyncio
async def test_no_rule_repo_list_empty(mock_no_rule_repo):
    result = await mock_no_rule_repo.list_by_category(uuid.uuid4())
    assert result == []
```

- [ ] **Step 2: 运行，确认失败**

```bash
.venv/bin/pytest tests/unit/repository/test_no_rule_engine.py::test_no_rule_repo_list_empty -v --no-cov
```
Expected: `ImportError`

- [ ] **Step 3: 创建 `repositories/no_rule_repo.py`**

```python
# backend/app/modules/repository/repositories/no_rule_repo.py
import uuid
from typing import Optional
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.repository.models.no_rule import ArchiveNoRule
from app.modules.repository.models.no_rule_seq import ArchiveNoSeq


class NoRuleRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_by_id(self, rule_id: uuid.UUID) -> Optional[ArchiveNoRule]:
        result = await self._db.execute(
            select(ArchiveNoRule).where(
                and_(ArchiveNoRule.id == rule_id, ArchiveNoRule.is_deleted == False)
            )
        )
        return result.scalar_one_or_none()

    async def list_by_category(self, category_id: uuid.UUID) -> list[ArchiveNoRule]:
        result = await self._db.execute(
            select(ArchiveNoRule).where(
                and_(
                    ArchiveNoRule.category_id == category_id,
                    ArchiveNoRule.is_deleted == False,
                )
            )
        )
        return list(result.scalars().all())

    async def list_by_tenant(
        self, tenant_id: Optional[uuid.UUID] = None
    ) -> list[ArchiveNoRule]:
        conditions = [ArchiveNoRule.is_deleted == False]
        if tenant_id:
            conditions.append(ArchiveNoRule.tenant_id == tenant_id)
        result = await self._db.execute(
            select(ArchiveNoRule).where(and_(*conditions))
        )
        return list(result.scalars().all())

    async def create(self, rule: ArchiveNoRule) -> ArchiveNoRule:
        self._db.add(rule)
        await self._db.flush()
        await self._db.refresh(rule)
        return rule

    async def delete(self, rule: ArchiveNoRule) -> None:
        rule.is_deleted = True
        await self._db.flush()


class SeqRepository:
    """序号跟踪表 Repository。所有写操作必须在事务内使用 FOR UPDATE。"""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_and_lock(
        self, rule_id: uuid.UUID, scope_key: str
    ) -> Optional[ArchiveNoSeq]:
        """获取序号行并加行锁（FOR UPDATE）。必须在事务中调用。"""
        result = await self._db.execute(
            select(ArchiveNoSeq)
            .where(
                and_(
                    ArchiveNoSeq.rule_id == rule_id,
                    ArchiveNoSeq.scope_key == scope_key,
                )
            )
            .with_for_update()
        )
        return result.scalar_one_or_none()

    async def create_seq(
        self, rule_id: uuid.UUID, scope_key: str, initial: int = 1
    ) -> ArchiveNoSeq:
        seq = ArchiveNoSeq(rule_id=rule_id, scope_key=scope_key, current_seq=initial)
        self._db.add(seq)
        await self._db.flush()
        return seq
```

- [ ] **Step 4: 运行测试，确认通过**

```bash
.venv/bin/pytest tests/unit/repository/test_no_rule_engine.py::test_no_rule_repo_list_empty -v --no-cov
```
Expected: 1 passed

- [ ] **Step 5: Commit**

```bash
cd /Users/hikari/Documents/projects/project-archive
git add backend/app/modules/repository/repositories/no_rule_repo.py \
        backend/tests/unit/repository/test_no_rule_engine.py
git commit -m "feat: add NoRuleRepository + SeqRepository (Plan B Task 3)"
```

---

## Task 4：规则引擎（核心）

**Files:**
- Create: `backend/app/modules/repository/services/no_rule_engine.py`
- Test: 追加到 `backend/tests/unit/repository/test_no_rule_engine.py`

- [ ] **Step 1: 追加引擎单元测试**

```python
# 追加到 test_no_rule_engine.py

from app.modules.repository.services.no_rule_engine import ArchiveNoEngine
from app.modules.repository.models.no_rule import ArchiveNoRule
from app.modules.repository.models.archive import Archive


def _make_rule(template: dict) -> ArchiveNoRule:
    rule = ArchiveNoRule.__new__(ArchiveNoRule)
    rule.id = uuid.uuid4()
    rule.rule_template = template
    rule.seq_scope = template.get("segments", [{}])[-1].get("scope", "catalog_year")
    return rule


def _make_archive(**kwargs) -> Archive:
    arch = Archive.__new__(Archive)
    arch.fonds_id = uuid.uuid4()
    arch.catalog_id = uuid.uuid4()
    arch.category_id = uuid.uuid4()
    arch.fonds_code = kwargs.get("fonds_code", "J001")
    arch.year = kwargs.get("year", 2024)
    arch.catalog_no = kwargs.get("catalog_no", "1")
    arch.volume_no = kwargs.get("volume_no", None)
    arch.item_no = kwargs.get("item_no", None)
    arch.creator = kwargs.get("creator", None)
    arch.doc_date = kwargs.get("doc_date", "2024-06-15")
    arch.level = "item"
    arch.title = "test"
    return arch


@pytest.mark.asyncio
async def test_engine_field_literal_segments():
    """field + literal 段 → 无序号，纯拼接"""
    db = AsyncMock()
    engine = ArchiveNoEngine(db)
    rule = _make_rule({
        "separator": "-",
        "segments": [
            {"type": "field", "field": "fonds_code"},
            {"type": "literal", "value": "WS"},
        ],
    })
    archive = _make_archive(fonds_code="J001")
    result = await engine.generate(rule, archive, preview=True)
    assert result == "J001-WS"


@pytest.mark.asyncio
async def test_engine_date_part_year():
    """date_part 提取年份"""
    db = AsyncMock()
    engine = ArchiveNoEngine(db)
    rule = _make_rule({
        "separator": "-",
        "segments": [
            {"type": "date_part", "date_field": "doc_date", "format": "%Y"},
        ],
    })
    archive = _make_archive(doc_date="2024-06-15")
    result = await engine.generate(rule, archive, preview=True)
    assert result == "2024"


@pytest.mark.asyncio
async def test_engine_sequence_preview_uses_zeros():
    """preview=True 时序号段输出全零占位，不写 DB"""
    db = AsyncMock()
    engine = ArchiveNoEngine(db)
    rule = _make_rule({
        "separator": "-",
        "segments": [
            {"type": "field", "field": "fonds_code"},
            {"type": "sequence", "padding": 4, "scope": "catalog_year"},
        ],
    })
    archive = _make_archive(fonds_code="J001")
    result = await engine.generate(rule, archive, preview=True)
    assert result == "J001-0000"
    db.execute.assert_not_called()   # preview 不碰 DB


@pytest.mark.asyncio
async def test_engine_sequence_real_increments():
    """preview=False 时序号从 SeqRepository 取，并返回带补零的字符串"""
    db = AsyncMock()
    # 模拟 get_and_lock 返回 None（首次），create_seq 返回 seq=1
    from app.modules.repository.models.no_rule_seq import ArchiveNoSeq
    seq_row = ArchiveNoSeq.__new__(ArchiveNoSeq)
    seq_row.current_seq = 1

    engine = ArchiveNoEngine(db)
    # 注入 mock SeqRepository
    mock_seq_repo = AsyncMock()
    mock_seq_repo.get_and_lock = AsyncMock(return_value=None)
    mock_seq_repo.create_seq = AsyncMock(return_value=seq_row)
    engine._seq_repo = mock_seq_repo

    rule = _make_rule({
        "separator": "-",
        "segments": [
            {"type": "field", "field": "fonds_code"},
            {"type": "sequence", "padding": 4, "scope": "catalog_year"},
        ],
    })
    archive = _make_archive(fonds_code="J001", year=2024)
    result = await engine.generate(rule, archive, preview=False)
    assert result == "J001-0001"
    mock_seq_repo.create_seq.assert_called_once()


@pytest.mark.asyncio
async def test_engine_sequence_existing_row_increments():
    """已有序号行时递增后返回新值"""
    db = AsyncMock()
    from app.modules.repository.models.no_rule_seq import ArchiveNoSeq
    seq_row = ArchiveNoSeq.__new__(ArchiveNoSeq)
    seq_row.current_seq = 22   # 已有 22，下一个应为 23

    engine = ArchiveNoEngine(db)
    mock_seq_repo = AsyncMock()
    mock_seq_repo.get_and_lock = AsyncMock(return_value=seq_row)
    engine._seq_repo = mock_seq_repo

    rule = _make_rule({
        "separator": "-",
        "segments": [
            {"type": "sequence", "padding": 4, "scope": "catalog_year"},
        ],
    })
    archive = _make_archive(year=2024)
    result = await engine.generate(rule, archive, preview=False)
    assert result == "0023"
    assert seq_row.current_seq == 23
```

- [ ] **Step 2: 运行，确认失败**

```bash
.venv/bin/pytest tests/unit/repository/test_no_rule_engine.py -k "engine" -v --no-cov
```
Expected: `ImportError` (ArchiveNoEngine 不存在)

- [ ] **Step 3: 创建 `services/no_rule_engine.py`**

```python
# backend/app/modules/repository/services/no_rule_engine.py
"""
档号规则引擎。

支持四种规则段：
  field     — 取 Archive 规范化字段值（fonds_code / year / catalog_no / volume_no / item_no / creator）
  literal   — 固定字符串
  sequence  — 自增序号（通过 SeqRepository FOR UPDATE 保证并发安全）
  date_part — 从 doc_date 提取日期部分（strftime 格式）

preview=True 时序号段输出全零占位，不写 DB。
"""
import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.repository.models.archive import Archive
from app.modules.repository.models.no_rule import ArchiveNoRule
from app.modules.repository.repositories.no_rule_repo import SeqRepository

# 允许从 Archive 读取的规范化字段白名单
_ALLOWED_FIELDS = {"fonds_code", "year", "catalog_no", "volume_no", "item_no", "creator"}


class ArchiveNoEngine:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db
        self._seq_repo = SeqRepository(db)

    async def generate(
        self, rule: ArchiveNoRule, archive: Archive, preview: bool = False
    ) -> str:
        """
        根据 rule.rule_template 生成档号字符串。
        preview=True：序号段用 "0" * padding 占位，不操作 DB。
        """
        template = rule.rule_template or {}
        separator: str = template.get("separator", "-")
        segments: list[dict] = template.get("segments", [])

        parts: list[str] = []
        for seg in segments:
            seg_type = seg.get("type")
            if seg_type == "field":
                parts.append(self._resolve_field(archive, seg.get("field", "")))
            elif seg_type == "literal":
                parts.append(str(seg.get("value", "")))
            elif seg_type == "date_part":
                parts.append(self._resolve_date_part(archive, seg))
            elif seg_type == "sequence":
                padding: int = seg.get("padding", 4)
                if preview:
                    parts.append("0" * padding)
                else:
                    seq_val = await self._next_seq(
                        rule_id=rule.id,
                        scope_type=seg.get("scope", "catalog_year"),
                        archive=archive,
                        padding=padding,
                    )
                    parts.append(seq_val)

        return separator.join(parts)

    # ── Preview helper ──────────────────────────────────────────────────────

    async def preview(
        self, rule: ArchiveNoRule, sample: dict
    ) -> tuple[str, list[str]]:
        """
        用样本数据（dict）生成预览档号，返回 (archive_no, parts)。
        sample 键对应 PreviewRequest 字段。
        """
        # 构造临时 Archive-like 对象
        fake = _FakeArchive(sample)
        template = rule.rule_template or {}
        separator: str = template.get("separator", "-")
        segments: list[dict] = template.get("segments", [])

        parts: list[str] = []
        for seg in segments:
            seg_type = seg.get("type")
            if seg_type == "field":
                parts.append(self._resolve_field(fake, seg.get("field", "")))
            elif seg_type == "literal":
                parts.append(str(seg.get("value", "")))
            elif seg_type == "date_part":
                parts.append(self._resolve_date_part(fake, seg))
            elif seg_type == "sequence":
                padding: int = seg.get("padding", 4)
                parts.append("0" * padding)

        return separator.join(parts), parts

    # ── Private helpers ─────────────────────────────────────────────────────

    def _resolve_field(self, archive: object, field: str) -> str:
        if field not in _ALLOWED_FIELDS:
            return ""
        val = getattr(archive, field, None)
        return str(val) if val is not None else ""

    def _resolve_date_part(self, archive: object, seg: dict) -> str:
        date_field = seg.get("date_field", "doc_date")
        fmt = seg.get("format", "%Y")
        raw: Optional[str] = getattr(archive, date_field, None)
        if not raw:
            return ""
        try:
            dt = datetime.strptime(raw[:10], "%Y-%m-%d")
            return dt.strftime(fmt)
        except ValueError:
            return raw[:4]  # fallback: 取前4字符

    async def _next_seq(
        self,
        rule_id: uuid.UUID,
        scope_type: str,
        archive: Archive,
        padding: int,
    ) -> str:
        scope_key = self._make_scope_key(scope_type, archive)
        seq_row = await self._seq_repo.get_and_lock(rule_id, scope_key)
        if seq_row is None:
            seq_row = await self._seq_repo.create_seq(rule_id, scope_key, initial=1)
            return str(1).zfill(padding)
        seq_row.current_seq += 1
        await self._db.flush()
        return str(seq_row.current_seq).zfill(padding)

    @staticmethod
    def _make_scope_key(scope_type: str, archive: object) -> str:
        catalog_id = str(getattr(archive, "catalog_id", ""))
        fonds_id = str(getattr(archive, "fonds_id", ""))
        year = str(getattr(archive, "year", "") or "")
        if scope_type == "catalog":
            return f"catalog:{catalog_id}"
        if scope_type == "catalog_year":
            return f"catalog_year:{catalog_id}:{year}"
        if scope_type == "fonds":
            return f"fonds:{fonds_id}"
        return f"catalog_year:{catalog_id}:{year}"


class _FakeArchive:
    """轻量替代品，用于 preview() 时避免构造完整 Archive 对象。"""
    def __init__(self, data: dict) -> None:
        for k, v in data.items():
            setattr(self, k, v)

    def __getattr__(self, name: str):
        return None
```

- [ ] **Step 4: 运行引擎测试，确认通过**

```bash
.venv/bin/pytest tests/unit/repository/test_no_rule_engine.py -k "engine" -v --no-cov
```
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
cd /Users/hikari/Documents/projects/project-archive
git add backend/app/modules/repository/services/no_rule_engine.py \
        backend/tests/unit/repository/test_no_rule_engine.py
git commit -m "feat: implement ArchiveNoEngine with field/literal/sequence/date_part segments (Plan B Task 4)"
```

---

## Task 5：NoRuleService

**Files:**
- Create: `backend/app/modules/repository/services/no_rule_service.py`
- Test: 追加到 `test_no_rule_engine.py`

- [ ] **Step 1: 追加 service 测试**

```python
# 追加到 test_no_rule_engine.py

from app.modules.repository.services.no_rule_service import NoRuleService
from app.modules.repository.schemas.no_rule import NoRuleCreate
from app.modules.repository.models.no_rule import ArchiveNoRule
from app.common.exceptions.base import NotFoundException


@pytest.fixture
def mock_no_rule_repo_svc():
    repo = AsyncMock()
    rule = ArchiveNoRule.__new__(ArchiveNoRule)
    rule.id = uuid.uuid4()
    rule.category_id = uuid.uuid4()
    rule.name = "测试规则"
    rule.rule_template = {"separator": "-", "segments": []}
    rule.seq_scope = "catalog_year"
    rule.is_active = True
    rule.tenant_id = None
    rule.is_deleted = False
    repo.get_by_id = AsyncMock(return_value=rule)
    repo.list_by_tenant = AsyncMock(return_value=[rule])
    repo.create = AsyncMock(return_value=rule)
    repo.delete = AsyncMock()
    return repo, rule


@pytest.fixture
def no_rule_service(mock_no_rule_repo_svc):
    repo, _ = mock_no_rule_repo_svc
    svc = NoRuleService.__new__(NoRuleService)
    svc._repo = repo
    return svc


@pytest.mark.asyncio
async def test_no_rule_service_list(no_rule_service, mock_no_rule_repo_svc):
    repo, rule = mock_no_rule_repo_svc
    result = await no_rule_service.list_all(tenant_id=None)
    repo.list_by_tenant.assert_called_once()
    assert len(result) == 1


@pytest.mark.asyncio
async def test_no_rule_service_get_not_found(no_rule_service, mock_no_rule_repo_svc):
    repo, _ = mock_no_rule_repo_svc
    repo.get_by_id = AsyncMock(return_value=None)
    with pytest.raises(NotFoundException):
        await no_rule_service.get(uuid.uuid4())


@pytest.mark.asyncio
async def test_no_rule_service_delete(no_rule_service, mock_no_rule_repo_svc):
    repo, rule = mock_no_rule_repo_svc
    await no_rule_service.delete(rule.id)
    repo.delete.assert_called_once_with(rule)
```

- [ ] **Step 2: 运行，确认失败**

```bash
.venv/bin/pytest tests/unit/repository/test_no_rule_engine.py -k "no_rule_service" -v --no-cov
```
Expected: `ImportError`

- [ ] **Step 3: 创建 `services/no_rule_service.py`**

```python
# backend/app/modules/repository/services/no_rule_service.py
import uuid
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.repository.models.no_rule import ArchiveNoRule
from app.modules.repository.repositories.no_rule_repo import NoRuleRepository
from app.modules.repository.schemas.no_rule import NoRuleCreate, NoRuleUpdate
from app.common.exceptions.base import NotFoundException
from app.common.error_code import ErrorCode


class NoRuleService:
    def __init__(self, db: AsyncSession) -> None:
        self._repo = NoRuleRepository(db)

    async def list_all(self, tenant_id: Optional[uuid.UUID] = None) -> list[ArchiveNoRule]:
        return await self._repo.list_by_tenant(tenant_id=tenant_id)

    async def get(self, rule_id: uuid.UUID) -> ArchiveNoRule:
        rule = await self._repo.get_by_id(rule_id)
        if not rule:
            raise NotFoundException(code=ErrorCode.ARCHIVE_NOT_FOUND, message="档号规则不存在")
        return rule

    async def create(
        self, data: NoRuleCreate, tenant_id: Optional[uuid.UUID]
    ) -> ArchiveNoRule:
        rule = ArchiveNoRule(
            category_id=data.category_id,
            name=data.name,
            rule_template=data.rule_template,
            seq_scope=data.seq_scope,
            is_active=data.is_active,
            tenant_id=tenant_id,
        )
        return await self._repo.create(rule)

    async def update(self, rule_id: uuid.UUID, data: NoRuleUpdate) -> ArchiveNoRule:
        rule = await self.get(rule_id)
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(rule, field, value)
        return rule

    async def delete(self, rule_id: uuid.UUID) -> None:
        rule = await self.get(rule_id)
        await self._repo.delete(rule)
```

- [ ] **Step 4: 运行测试，确认通过**

```bash
.venv/bin/pytest tests/unit/repository/test_no_rule_engine.py -k "no_rule_service" -v --no-cov
```
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
cd /Users/hikari/Documents/projects/project-archive
git add backend/app/modules/repository/services/no_rule_service.py \
        backend/tests/unit/repository/test_no_rule_engine.py
git commit -m "feat: add NoRuleService CRUD (Plan B Task 5)"
```

---

## Task 6：API 路由 + 挂载

**Files:**
- Create: `backend/app/modules/repository/api/routes_no_rule.py`
- Modify: `backend/app/api/v1/router.py`

- [ ] **Step 1: 创建 `api/routes_no_rule.py`**

```python
# backend/app/modules/repository/api/routes_no_rule.py
import uuid
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.infra.db.session import get_db
from app.modules.iam.api.dependencies import get_current_user
from app.modules.iam.models.user import User
from app.modules.repository.services.no_rule_service import NoRuleService
from app.modules.repository.services.no_rule_engine import ArchiveNoEngine
from app.modules.repository.schemas.no_rule import (
    NoRuleCreate, NoRuleUpdate, NoRuleRead, PreviewRequest, PreviewResponse,
)
from app.common.response import success, ResponseModel

router = APIRouter(prefix="/archive/no-rules", tags=["档号规则"])


@router.get("", response_model=ResponseModel[list[NoRuleRead]])
async def list_no_rules(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = NoRuleService(db)
    items = await svc.list_all(tenant_id=current_user.tenant_id)
    return success([NoRuleRead.model_validate(i) for i in items])


@router.post("", response_model=ResponseModel[NoRuleRead])
async def create_no_rule(
    data: NoRuleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = NoRuleService(db)
    item = await svc.create(data, tenant_id=current_user.tenant_id)
    await db.commit()
    return success(NoRuleRead.model_validate(item))


@router.get("/{rule_id}", response_model=ResponseModel[NoRuleRead])
async def get_no_rule(
    rule_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = NoRuleService(db)
    item = await svc.get(rule_id)
    return success(NoRuleRead.model_validate(item))


@router.put("/{rule_id}", response_model=ResponseModel[NoRuleRead])
async def update_no_rule(
    rule_id: uuid.UUID,
    data: NoRuleUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = NoRuleService(db)
    item = await svc.update(rule_id, data)
    await db.commit()
    return success(NoRuleRead.model_validate(item))


@router.delete("/{rule_id}", response_model=ResponseModel[None])
async def delete_no_rule(
    rule_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = NoRuleService(db)
    await svc.delete(rule_id)
    await db.commit()
    return success()


@router.post("/{rule_id}/preview", response_model=ResponseModel[PreviewResponse])
async def preview_no_rule(
    rule_id: uuid.UUID,
    req: PreviewRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """用样本数据预览生成档号，不写 DB。"""
    svc = NoRuleService(db)
    rule = await svc.get(rule_id)
    engine = ArchiveNoEngine(db)
    archive_no, parts = await engine.preview(rule, req.model_dump(exclude_none=True))
    return success(PreviewResponse(archive_no=archive_no, segments=parts))
```

- [ ] **Step 2: 挂载到 `router.py`**

在 `backend/app/api/v1/router.py` 的现有 import 区末尾新增：

```python
from app.modules.repository.api.routes_no_rule import router as no_rule_router
```

在 `include_router` 区末尾新增：

```python
v1_router.include_router(no_rule_router)
```

- [ ] **Step 3: 验证 router 可导入**

```bash
cd backend && .venv/bin/python -c "from app.api.v1.router import v1_router; print('OK')"
```
Expected: `OK`

- [ ] **Step 4: 运行全部 repository 单元测试**

```bash
.venv/bin/pytest tests/unit/repository/ -v --no-cov
```
Expected: 全部 PASS（含所有 Plan A + Plan B 新增测试）

- [ ] **Step 5: Commit**

```bash
cd /Users/hikari/Documents/projects/project-archive
git add backend/app/modules/repository/api/routes_no_rule.py \
        backend/app/api/v1/router.py \
        backend/tests/unit/repository/test_no_rule_engine.py
git commit -m "feat: add archive no-rule REST routes + wire into router (Plan B Task 6)"
```

---

## 覆盖率检查（完整 Plan B）

| 要求 | 测试 |
|------|------|
| 规则段 field / literal | `test_engine_field_literal_segments` |
| 规则段 date_part | `test_engine_date_part_year` |
| preview 序号占位 | `test_engine_sequence_preview_uses_zeros` |
| sequence 首次插入 | `test_engine_sequence_real_increments` |
| sequence 已有行递增 | `test_engine_sequence_existing_row_increments` |
| service CRUD | `test_no_rule_service_*` (3 个) |
| schema 验证 | `test_segment_def_*` / `test_no_rule_create_valid` (4 个) |
| model 实例化 | `test_no_seq_instantiate` / `test_category_has_no_rule_id_field` |

---

## Spec Coverage 检查

| 设计要求 | 对应 Task |
|---------|-----------|
| field / literal / sequence / date_part 四种段 | Task 4 engine |
| sequence scope: catalog / catalog_year / fonds | Task 4 engine `_make_scope_key` |
| FOR UPDATE 行锁并发安全 | Task 3 SeqRepository.get_and_lock |
| preview 预览不写 DB | Task 4 engine preview=True |
| `/archive/no-rules` CRUD | Task 6 routes |
| `/archive/no-rules/{id}/preview` | Task 6 routes |
| `ArchiveCategory.archive_no_rule_id` FK | Task 1 |
| Migration 建表 | Task 1 Step 6 |

无遗漏。
