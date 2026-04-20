import uuid
from typing import Optional

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.collection.models.import_task import ImportTask


class ImportTaskRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create(self, task: ImportTask) -> ImportTask:
        self._db.add(task)
        await self._db.flush()
        await self._db.refresh(task)
        return task

    async def get_by_id(
        self, task_id: uuid.UUID, tenant_id: Optional[uuid.UUID] = None
    ) -> Optional[ImportTask]:
        conds = [ImportTask.id == task_id, ImportTask.is_deleted == False]
        if tenant_id is not None:
            conds.append(ImportTask.tenant_id == tenant_id)
        result = await self._db.execute(select(ImportTask).where(and_(*conds)))
        return result.scalar_one_or_none()

    async def list_by_tenant(
        self, tenant_id: Optional[uuid.UUID], skip: int = 0, limit: int = 20
    ) -> list[ImportTask]:
        conds = [ImportTask.is_deleted == False]
        if tenant_id is not None:
            conds.append(ImportTask.tenant_id == tenant_id)
        result = await self._db.execute(
            select(ImportTask)
            .where(and_(*conds))
            .order_by(ImportTask.create_time.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())
