"""
批量导入服务（同步部分）。

负责前三步：
  1. upload   — 保存文件、解析列头、创建 ImportTask(pending)
  2. mapping  — 保存映射快照到 task.mapping_snapshot
  3. dry_run  — 预检所有行，返回报告，不写库

异步执行（第 4 步）由 Celery 任务 import_task.execute_import 完成。
"""
import uuid
from datetime import timezone, datetime
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.error_code import ErrorCode
from app.common.exceptions.base import NotFoundException, ValidationException
from app.infra.storage.factory import storage
from app.modules.collection.models.import_task import ImportTask
from app.modules.collection.models.mapping_template import FieldMappingTemplate
from app.modules.collection.repositories.import_repo import ImportTaskRepository
from app.modules.collection.schemas.import_schema import (
    ColumnMapping, DryRunResponse, DryRunRow, UploadResponse,
)
from app.modules.collection.services.file_parser import parse_file
from app.modules.collection.services.mapping_service import (
    MappingTemplateRepository, auto_match,
)
from app.modules.repository.models.archive import Archive

_IMPORT_BUCKET = "import-staging"

# 必填字段（档案写入最低要求）
_REQUIRED_FIELDS = {"title"}

# 支持的字段 → 对应 Archive 列名
_FIELD_MAP = {
    "title", "archive_no", "fonds_code", "catalog_no", "volume_no",
    "item_no", "year", "creator", "doc_date", "pages",
    "security_level", "retention_period",
}


class ImportService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db
        self._repo = ImportTaskRepository(db)
        self._tpl_repo = MappingTemplateRepository(db)

    # ── Step 1: 上传文件 ──────────────────────────────────────────────

    async def upload(
        self,
        file_bytes: bytes,
        filename: str,
        category_id: uuid.UUID,
        fonds_id: uuid.UUID,
        catalog_id: uuid.UUID,
        operator_id: uuid.UUID,
        tenant_id: Optional[uuid.UUID],
    ) -> UploadResponse:
        columns, _ = parse_file(file_bytes, filename)

        # 存原始文件到对象存储
        import io
        key = storage.generate_object_key("import", filename)
        storage.save(io.BytesIO(file_bytes), key, _IMPORT_BUCKET, "application/octet-stream")

        task = ImportTask(
            category_id=category_id,
            fonds_id=fonds_id,
            catalog_id=catalog_id,
            operator_id=operator_id,
            tenant_id=tenant_id,
            status="pending",
            file_key=key,
            original_filename=filename,
        )
        task = await self._repo.create(task)
        return UploadResponse(task_id=task.id, columns=columns)

    # ── Step 2: 保存映射 + 自动匹配建议 ────────────────────────────────

    async def save_mapping(
        self,
        task_id: uuid.UUID,
        mappings: list[ColumnMapping],
        save_as_template: Optional[str],
        tenant_id: Optional[uuid.UUID],
    ) -> None:
        task = await self._get_task(task_id, tenant_id)
        snapshot = [{"source_col": m.source_col, "target_field": m.target_field} for m in mappings]
        task.mapping_snapshot = snapshot

        if save_as_template and save_as_template.strip():
            tpl = FieldMappingTemplate(
                category_id=task.category_id,
                name=save_as_template.strip(),
                mappings=snapshot,
                tenant_id=tenant_id,
            )
            self._db.add(tpl)

        await self._db.flush()

    # ── Step 3: Dry-run 预检 ─────────────────────────────────────────

    async def dry_run(
        self,
        task_id: uuid.UUID,
        tenant_id: Optional[uuid.UUID],
    ) -> DryRunResponse:
        task = await self._get_task(task_id, tenant_id)
        if not task.file_key:
            raise ValidationException(message="导入文件不存在")
        if not task.mapping_snapshot:
            raise ValidationException(message="请先完成字段映射")

        # 从对象存储读取文件
        file_bytes = storage.get(task.file_key, _IMPORT_BUCKET)
        _, rows = parse_file(file_bytes, task.original_filename or "file.csv")

        mapping: dict[str, Optional[str]] = {
            m["source_col"]: m["target_field"]
            for m in task.mapping_snapshot
        }

        ok = warning = error = 0
        sample_errors: list[DryRunRow] = []

        for i, row in enumerate(rows, start=2):  # 第 2 行起（第 1 行是表头）
            mapped = _apply_mapping(row, mapping)
            issues = _validate_row(mapped)
            if not issues:
                ok += 1
            elif any(s == "error" for s, _ in issues):
                error += 1
                if len(sample_errors) < 20:
                    sample_errors.append(DryRunRow(row=i, status="error", message="; ".join(m for _, m in issues)))
            else:
                warning += 1

        task.total = len(rows)
        await self._db.flush()

        return DryRunResponse(
            task_id=task_id,
            total=len(rows),
            ok=ok,
            warning=warning,
            error=error,
            sample_errors=sample_errors,
        )

    # ── 获取任务 ─────────────────────────────────────────────────────

    async def get_task(
        self, task_id: uuid.UUID, tenant_id: Optional[uuid.UUID]
    ) -> ImportTask:
        return await self._get_task(task_id, tenant_id)

    async def _get_task(
        self, task_id: uuid.UUID, tenant_id: Optional[uuid.UUID]
    ) -> ImportTask:
        task = await self._repo.get_by_id(task_id, tenant_id)
        if not task:
            raise NotFoundException(code=ErrorCode.INTERNAL_ERROR, message="导入任务不存在")
        return task


# ── 工具函数 ──────────────────────────────────────────────────────────────────

def _apply_mapping(row: dict[str, str], mapping: dict[str, Optional[str]]) -> dict[str, str]:
    """将文件行按映射转换为目标字段字典。ext_fields 单独收集。"""
    result: dict[str, str] = {}
    for src_col, val in row.items():
        target = mapping.get(src_col)
        if target and val is not None:
            result[target] = val
    return result


def _validate_row(mapped: dict[str, str]) -> list[tuple[str, str]]:
    """校验单行数据，返回 [(severity, message)] 列表，空列表=OK。"""
    issues = []
    for field in _REQUIRED_FIELDS:
        if not mapped.get(field, "").strip():
            issues.append(("error", f"{field} 不能为空"))
    year = mapped.get("year", "")
    if year and not year.isdigit():
        issues.append(("error", "year 必须为数字"))
    return issues


def build_archive_from_row(
    mapped: dict[str, str],
    fonds_id: uuid.UUID,
    catalog_id: uuid.UUID,
    category_id: uuid.UUID,
    fonds_code: str,
    tenant_id: Optional[uuid.UUID],
) -> Archive:
    """从映射后的字段字典构建 Archive 实例（不包含 archive_no，由引擎生成）。"""
    ext: dict = {}
    std: dict = {}
    for k, v in mapped.items():
        if k.startswith("ext."):
            ext[k[4:]] = v
        else:
            std[k] = v

    return Archive(
        fonds_id=fonds_id,
        catalog_id=catalog_id,
        category_id=category_id,
        fonds_code=fonds_code,
        tenant_id=tenant_id,
        level="item",
        title=std.get("title", ""),
        creator=std.get("creator"),
        year=int(std["year"]) if std.get("year", "").isdigit() else None,
        catalog_no=std.get("catalog_no"),
        volume_no=std.get("volume_no"),
        item_no=std.get("item_no"),
        doc_date=std.get("doc_date"),
        pages=int(std["pages"]) if std.get("pages", "").isdigit() else None,
        security_level=std.get("security_level", "public"),
        retention_period=std.get("retention_period", "permanent"),
        ext_fields=ext or None,
    )
