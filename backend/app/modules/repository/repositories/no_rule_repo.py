import uuid
from typing import Optional

from sqlalchemy import and_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.repository.models.no_rule import ArchiveNoRule
from app.modules.repository.models.no_rule_seq import ArchiveNoSeq


class NoRuleRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_by_id(
        self,
        rule_id: uuid.UUID,
        tenant_id: Optional[uuid.UUID] = None,
    ) -> Optional[ArchiveNoRule]:
        conditions = [ArchiveNoRule.id == rule_id, ArchiveNoRule.is_deleted == False]
        if tenant_id is not None:
            conditions.append(ArchiveNoRule.tenant_id == tenant_id)
        result = await self._db.execute(
            select(ArchiveNoRule).where(and_(*conditions))
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
        if tenant_id is not None:
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
    """序号跟踪表 Repository。使用 PostgreSQL upsert 保证并发安全。"""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def increment(
        self, rule_id: uuid.UUID, scope_key: str
    ) -> int:
        """
        原子性地插入或递增序号，返回分配到的序号值。
        首次插入时 current_seq=1；已有行时 current_seq+1。
        使用 INSERT ... ON CONFLICT DO UPDATE 消除并发竞争，无需 SELECT FOR UPDATE。
        """
        stmt = (
            insert(ArchiveNoSeq)
            .values(rule_id=rule_id, scope_key=scope_key, current_seq=1)
            .on_conflict_do_update(
                constraint="uq_no_seq_rule_scope",
                set_={"current_seq": ArchiveNoSeq.current_seq + 1},
            )
            .returning(ArchiveNoSeq.current_seq)
        )
        result = await self._db.execute(stmt)
        return result.scalar_one()
