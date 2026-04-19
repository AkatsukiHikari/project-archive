import uuid
from typing import Optional

from sqlalchemy import and_, select
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
