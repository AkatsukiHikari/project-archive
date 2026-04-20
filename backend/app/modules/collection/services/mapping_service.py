"""
字段映射服务。

功能：
  1. 根据档案门类的 field_schema 构建目标字段列表
  2. 对文件列头与目标字段做自动匹配（基于字符串相似度）
  3. 保存 / 查询映射模板
"""
from difflib import SequenceMatcher
from typing import Optional
import uuid

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.collection.models.mapping_template import FieldMappingTemplate
from app.modules.repository.models.archive import Archive

# DA/T 规范化字段（所有门类通用）
_BASE_FIELDS: list[dict] = [
    {"name": "title",            "label": "题名"},
    {"name": "archive_no",       "label": "档号"},
    {"name": "fonds_code",       "label": "全宗号"},
    {"name": "catalog_no",       "label": "目录号"},
    {"name": "volume_no",        "label": "案卷号"},
    {"name": "item_no",          "label": "件号"},
    {"name": "year",             "label": "年度"},
    {"name": "creator",          "label": "责任者"},
    {"name": "doc_date",         "label": "文件日期"},
    {"name": "pages",            "label": "页数"},
    {"name": "security_level",   "label": "密级"},
    {"name": "retention_period", "label": "保管期限"},
]


def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def auto_match(source_columns: list[str], category_field_schema: Optional[list]) -> list[dict]:
    """
    自动将文件列头与目标字段匹配。
    返回 [{source_col, target_field, confidence}]，confidence < 0.5 时 target_field=None。
    """
    targets: list[dict] = list(_BASE_FIELDS)
    if category_field_schema:
        for f in category_field_schema:
            targets.append({"name": f"ext.{f['name']}", "label": f.get("label", f["name"])})

    result = []
    for col in source_columns:
        best_field: Optional[str] = None
        best_score = 0.0
        for t in targets:
            for cand in (t["name"], t["label"]):
                score = _similarity(col, cand)
                if score > best_score:
                    best_score = score
                    best_field = t["name"]
        result.append({
            "source_col": col,
            "target_field": best_field if best_score >= 0.5 else None,
            "confidence": round(best_score, 2),
        })
    return result


class MappingTemplateRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def list_by_category(
        self, category_id: uuid.UUID, tenant_id: Optional[uuid.UUID]
    ) -> list[FieldMappingTemplate]:
        conds = [
            FieldMappingTemplate.category_id == category_id,
            FieldMappingTemplate.is_deleted == False,
        ]
        if tenant_id is not None:
            conds.append(FieldMappingTemplate.tenant_id == tenant_id)
        result = await self._db.execute(select(FieldMappingTemplate).where(and_(*conds)))
        return list(result.scalars().all())

    async def create(self, tpl: FieldMappingTemplate) -> FieldMappingTemplate:
        self._db.add(tpl)
        await self._db.flush()
        return tpl

    async def get_default(
        self, category_id: uuid.UUID, tenant_id: Optional[uuid.UUID]
    ) -> Optional[FieldMappingTemplate]:
        conds = [
            FieldMappingTemplate.category_id == category_id,
            FieldMappingTemplate.is_default == True,
            FieldMappingTemplate.is_deleted == False,
        ]
        if tenant_id is not None:
            conds.append(FieldMappingTemplate.tenant_id == tenant_id)
        result = await self._db.execute(
            select(FieldMappingTemplate).where(and_(*conds)).limit(1)
        )
        return result.scalar_one_or_none()
