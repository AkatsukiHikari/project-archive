"""档案整理服务：批量修改字段 / 按档号规则批量重编 / 归档入库（暂存库→正式库）。"""

import logging
import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.error_code import ErrorCode
from app.common.exceptions.base import NotFoundException, ValidationException
from app.modules.repository.models.archive import (Archive, ArchiveAttachment,
                                                   ArchiveStaging)
from app.modules.repository.repositories.no_rule_repo import (NoRuleRepository,
                                                              SeqRepository)
from app.modules.repository.schemas.organize import (BatchUpdateRequest,
                                                     RenumberRequest,
                                                     RenumberRow)
from app.modules.repository.services.es_sync_service import sync_one
from app.modules.repository.services.no_rule_engine import ArchiveNoEngine

logger = logging.getLogger(__name__)

BATCH_FIELDS = ("MJ", "BGQX", "RZZ", "ND", "WJRQ")


class OrganizeService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── 批量修改字段 ──────────────────────────────────────────────────────────

    async def batch_update(
        self, body: BatchUpdateRequest, tenant_id: Optional[uuid.UUID]
    ) -> int:
        values = {
            f: getattr(body, f) for f in BATCH_FIELDS if getattr(body, f) is not None
        }
        if not values:
            raise ValidationException(message="至少指定一个要修改的字段")

        archives = await self._load_staging(body.ids, tenant_id)
        for a in archives:
            for field, value in values.items():
                setattr(a, field, value)
        await self.db.flush()
        for a in archives:
            await sync_one(a)
        return len(archives)

    # ── 批量重编档号 ──────────────────────────────────────────────────────────

    async def renumber_preview(
        self, body: RenumberRequest, tenant_id: Optional[uuid.UUID]
    ) -> list[RenumberRow]:
        rule, archives = await self._renumber_load(body, tenant_id)
        engine = ArchiveNoEngine(self.db)

        rows: list[RenumberRow] = []
        new_dhs: list[str] = []
        for idx, a in enumerate(archives):
            dh_new = await engine.generate(rule, a, seq_override=body.start_seq + idx)
            new_dhs.append(dh_new)
            rows.append(
                RenumberRow(id=a.id, TM=a.TM, WJRQ=a.WJRQ, DH_old=a.DH, DH_new=dh_new)
            )

        conflicts = await self._find_dh_conflicts(
            new_dhs, exclude_ids={a.id for a in archives}
        )
        for row in rows:
            row.conflict = row.DH_new in conflicts
        return rows

    async def renumber_apply(
        self, body: RenumberRequest, tenant_id: Optional[uuid.UUID]
    ) -> int:
        rows = await self.renumber_preview(body, tenant_id)
        conflict_dhs = [r.DH_new for r in rows if r.conflict]
        if conflict_dhs:
            raise ValidationException(
                message=f"新档号与现有档案冲突：{('、'.join(conflict_dhs[:5]))}"
                + ("…" if len(conflict_dhs) > 5 else ""),
            )

        rule, archives = await self._renumber_load(body, tenant_id)
        archive_map = {a.id: a for a in archives}
        for row in rows:
            archive_map[row.id].DH = row.DH_new
        await self.db.flush()

        await self._raise_seq_counters(rule, archives, body.start_seq + len(rows) - 1)
        for a in archives:
            await sync_one(a)
        return len(rows)

    async def _renumber_load(
        self, body: RenumberRequest, tenant_id: Optional[uuid.UUID]
    ) -> tuple[object, list[ArchiveStaging]]:
        if not body.catalog_id and not body.ids and not body.query:
            raise ValidationException(message="请勾选档案、指定查询条件或选择目录")

        rule = await NoRuleRepository(self.db).get_by_id(body.rule_id)
        if not rule:
            raise NotFoundException(
                code=ErrorCode.ARCHIVE_NO_RULE_NOT_FOUND, message="档号规则不存在"
            )

        stmt = select(ArchiveStaging)
        if body.ids:
            stmt = stmt.where(
                ArchiveStaging.id.in_(body.ids),
                ArchiveStaging.is_deleted.is_(False),
            )
            if tenant_id:
                stmt = stmt.where(ArchiveStaging.tenant_id == tenant_id)
        elif body.query:
            # 按当前查询条件全量应用（与著录列表同一套条件，跨页生效）
            from sqlalchemy import and_

            from app.modules.repository.repositories.archive_repo import (
                ArchiveRepository,
            )

            conditions = ArchiveRepository.build_conditions(body.query, tenant_id)
            stmt = stmt.where(and_(*conditions))
        else:
            stmt = stmt.where(
                ArchiveStaging.catalog_id == body.catalog_id,
                ArchiveStaging.is_deleted.is_(False),
            )
            if tenant_id:
                stmt = stmt.where(ArchiveStaging.tenant_id == tenant_id)

        # 整理惯例：按文件日期 → 题名 排序后连续编号
        stmt = stmt.order_by(
            ArchiveStaging.WJRQ.asc().nulls_last(),
            ArchiveStaging.TM.asc(),
        )
        archives = list((await self.db.execute(stmt)).scalars())
        if not archives:
            raise ValidationException(message="所选范围内没有待整理档案")
        return rule, archives

    async def _find_dh_conflicts(
        self, new_dhs: list[str], exclude_ids: set[uuid.UUID]
    ) -> set[str]:
        """新档号若已被范围之外的暂存/正式档案占用，视为冲突。"""
        conflicts: set[str] = set()
        staging = (
            (
                await self.db.execute(
                    select(ArchiveStaging.DH).where(
                        ArchiveStaging.DH.in_(new_dhs),
                        ArchiveStaging.is_deleted.is_(False),
                        ArchiveStaging.id.not_in(exclude_ids),
                    )
                )
            )
            .scalars()
            .all()
        )
        formal = (
            (
                await self.db.execute(
                    select(Archive.DH).where(
                        Archive.DH.in_(new_dhs), Archive.is_deleted.is_(False)
                    )
                )
            )
            .scalars()
            .all()
        )
        conflicts.update(staging)
        conflicts.update(formal)
        return conflicts

    async def _raise_seq_counters(
        self, rule, archives: list[ArchiveStaging], max_seq: int
    ) -> None:
        """重编后抬升序号器，避免后续接收按旧计数撞号。"""
        template = rule.rule_template or {}
        seq_seg = next(
            (s for s in template.get("segments", []) if s.get("type") == "sequence"),
            None,
        )
        if not seq_seg:
            return
        scope_type = seq_seg.get("scope", "catalog_year")
        seq_repo = SeqRepository(self.db)
        scope_keys = {ArchiveNoEngine._make_scope_key(scope_type, a) for a in archives}
        for key in scope_keys:
            await seq_repo.raise_to(rule.id, key, max_seq)

    # ── 归档入库 ──────────────────────────────────────────────────────────────

    async def archive_to_formal(
        self, ids: list[uuid.UUID], user_id: uuid.UUID, tenant_id: Optional[uuid.UUID]
    ) -> list[dict]:
        """暂存库 → 正式库。逐条校验，失败不阻断其余；保留原 UUID。"""
        archives = await self._load_staging(ids, tenant_id)
        results: list[dict] = []
        for staging in archives:
            reason = await self._validate_promotion(staging)
            if reason:
                results.append(
                    {
                        "id": staging.id,
                        "DH": staging.DH,
                        "TM": staging.TM,
                        "status": "failed",
                        "reason": reason,
                    }
                )
                continue

            formal = Archive(
                id=staging.id,  # 保留 UUID：附件/调阅篮/ES 文档引用全部无需迁移
                ND=staging.ND,
                fonds_id=staging.fonds_id,
                catalog_id=staging.catalog_id,
                category_id=staging.category_id,
                DH=staging.DH,
                QZH=staging.QZH,
                TM=staging.TM,
                RZZ=staging.RZZ,
                WJRQ=staging.WJRQ,
                YS=staging.YS,
                MJ=staging.MJ,
                BGQX=staging.BGQX,
                status="archived",
                ext_fields=staging.ext_fields,
                embedding_status=staging.embedding_status,
                tenant_id=staging.tenant_id,
                create_by=user_id,
            )
            self.db.add(formal)
            await self.db.flush()

            attachments = (
                (
                    await self.db.execute(
                        select(ArchiveAttachment).where(
                            ArchiveAttachment.archive_id == staging.id,
                            ArchiveAttachment.is_deleted.is_(False),
                        )
                    )
                )
                .scalars()
                .all()
            )
            for att in attachments:
                att.is_staging = False

            staging.status = "archived"
            staging.is_deleted = True
            results.append(
                {
                    "id": staging.id,
                    "DH": staging.DH,
                    "TM": staging.TM,
                    "status": "ok",
                    "reason": None,
                }
            )
            await sync_one(formal)
        return results

    async def _validate_promotion(self, staging: ArchiveStaging) -> Optional[str]:
        if staging.ND is None:
            return "年度（ND）为空，正式库按年度分区，必填"
        if not staging.DH:
            return "档号（DH）为空，请先编号"
        if not await self._partition_exists(staging.ND):
            return f"正式库缺少 {staging.ND} 年度分区，请联系管理员创建"
        dup = (
            await self.db.execute(
                select(Archive.id)
                .where(Archive.DH == staging.DH, Archive.is_deleted.is_(False))
                .limit(1)
            )
        ).scalar_one_or_none()
        if dup:
            return f"档号 {staging.DH} 在正式库已存在"
        return None

    async def _partition_exists(self, nd: int) -> bool:
        from sqlalchemy import text

        result = await self.db.execute(
            text("SELECT to_regclass(:name)"), {"name": f"repo_archive_{nd}"}
        )
        return result.scalar_one_or_none() is not None

    # ── 内部 ──────────────────────────────────────────────────────────────────

    async def _load_staging(
        self, ids: list[uuid.UUID], tenant_id: Optional[uuid.UUID]
    ) -> list[ArchiveStaging]:
        stmt = select(ArchiveStaging).where(
            ArchiveStaging.id.in_(ids), ArchiveStaging.is_deleted.is_(False)
        )
        if tenant_id:
            stmt = stmt.where(ArchiveStaging.tenant_id == tenant_id)
        archives = list((await self.db.execute(stmt)).scalars())
        if not archives:
            raise NotFoundException(
                code=ErrorCode.ARCHIVE_NOT_FOUND, message="所选档案不存在"
            )
        return archives
