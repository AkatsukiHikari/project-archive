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
        fmt = seg.get("date_format", "%Y")
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
            return str(seq_row.current_seq).zfill(padding)
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
