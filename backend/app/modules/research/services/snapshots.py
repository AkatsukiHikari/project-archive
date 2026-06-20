"""选材/引用共用：取一条源档案的冗余快照（先暂存库后正式库）。"""

import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.repository.models.archive import Archive, ArchiveStaging

SNAPSHOT_FIELDS = ("DH", "TM", "RZZ", "ND", "WJRQ", "QZH")


async def archive_snapshot(db: AsyncSession, archive_id: uuid.UUID) -> Optional[dict]:
    for model in (ArchiveStaging, Archive):
        a = (
            (
                await db.execute(
                    select(model).where(
                        model.id == archive_id, model.is_deleted.is_(False)
                    )
                )
            )
            .scalars()
            .first()
        )
        if a:
            return {f: getattr(a, f) for f in SNAPSHOT_FIELDS}
    return None
