"""出入库记录。

手动登记（修复/数字化/移库/盘点出入库），以及供利用模块调用的借阅联动：
  borrow_lend  → 自动生成借阅"出库"记录
  borrow_return → 回写对应出库记录为"已归还"
"""

import uuid
from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.error_code import ErrorCode
from app.common.exceptions.base import NotFoundException
from app.modules.storage.models import StorageInout
from app.modules.storage.schemas.vault import InoutCreate


class InoutService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_records(
        self,
        tenant_id: Optional[uuid.UUID],
        direction: Optional[str] = None,
        biz_type: Optional[str] = None,
        status: Optional[str] = None,
        keyword: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[int, list[StorageInout]]:
        stmt = select(StorageInout).where(StorageInout.is_deleted.is_(False))
        if tenant_id:
            stmt = stmt.where(StorageInout.tenant_id == tenant_id)
        if direction:
            stmt = stmt.where(StorageInout.direction == direction)
        if biz_type:
            stmt = stmt.where(StorageInout.biz_type == biz_type)
        if status:
            stmt = stmt.where(StorageInout.status == status)
        if keyword:
            like = f"%{keyword}%"
            stmt = stmt.where(
                StorageInout.TM.ilike(like)
                | StorageInout.DH.ilike(like)
                | StorageInout.record_no.ilike(like)
            )
        total = (
            await self.db.execute(select(func.count()).select_from(stmt.subquery()))
        ).scalar_one()
        records = (
            (
                await self.db.execute(
                    stmt.order_by(StorageInout.create_time.desc())
                    .offset(skip)
                    .limit(limit)
                )
            )
            .scalars()
            .all()
        )
        return total, list(records)

    async def create_record(
        self, body: InoutCreate, user_id: uuid.UUID, tenant_id: Optional[uuid.UUID]
    ) -> StorageInout:
        now = datetime.now(timezone.utc)
        record = StorageInout(
            record_no=await self._next_no(body.direction),
            direction=body.direction,
            biz_type=body.biz_type,
            archive_id=body.archive_id,
            DH=body.DH,
            TM=body.TM,
            qty=body.qty,
            vault_id=body.vault_id,
            counterparty=body.counterparty,
            expected_return=body.expected_return,
            notes=body.notes,
            operator_id=user_id,
            tenant_id=tenant_id,
        )
        if body.direction == "out":
            record.out_time = now
            record.status = "out"
        else:
            record.in_time = now
            record.status = "done"
        self.db.add(record)
        await self.db.flush()
        return record

    async def mark_returned(
        self, record_id: uuid.UUID, user_id: uuid.UUID, tenant_id: Optional[uuid.UUID]
    ) -> StorageInout:
        stmt = select(StorageInout).where(
            StorageInout.id == record_id, StorageInout.is_deleted.is_(False)
        )
        if tenant_id:
            stmt = stmt.where(StorageInout.tenant_id == tenant_id)
        record = (await self.db.execute(stmt)).scalars().first()
        if not record:
            raise NotFoundException(
                code=ErrorCode.INOUT_RECORD_NOT_FOUND, message="出入库记录不存在"
            )
        record.status = "returned"
        record.in_time = datetime.now(timezone.utc)
        await self.db.flush()
        return record

    async def _next_no(self, direction: str) -> str:
        prefix = ("CK" if direction == "out" else "RK") + date.today().strftime(
            "%Y%m%d"
        )
        count = (
            await self.db.execute(
                select(func.count())
                .select_from(StorageInout)
                .where(StorageInout.record_no.like(f"{prefix}%"))
            )
        ).scalar_one()
        return f"{prefix}{count + 1:03d}"

    # ── 借阅联动（由 ApplicationService 调用）─────────────────────────────────

    async def on_borrow_lend(
        self,
        app_id: uuid.UUID,
        borrower: str,
        items: list[dict],
        due: Optional[datetime],
        user_id: Optional[uuid.UUID],
        tenant_id: Optional[uuid.UUID],
    ) -> None:
        """借出时为每件调阅档案生成一条借阅出库记录。"""
        now = datetime.now(timezone.utc)
        for it in items:
            self.db.add(
                StorageInout(
                    record_no=await self._next_no("out"),
                    direction="out",
                    biz_type="borrow",
                    archive_id=it.get("archive_id"),
                    DH=it.get("DH"),
                    TM=it.get("TM"),
                    qty=1,
                    counterparty=borrower,
                    related_app_id=app_id,
                    status="out",
                    out_time=now,
                    expected_return=due,
                    operator_id=user_id,
                    tenant_id=tenant_id,
                    notes="借阅出库（利用模块自动生成）",
                )
            )

    async def on_borrow_return(
        self, app_id: uuid.UUID, tenant_id: Optional[uuid.UUID]
    ) -> None:
        """归还时把该申请关联的在外出库记录全部回写为已归还。"""
        stmt = select(StorageInout).where(
            StorageInout.related_app_id == app_id,
            StorageInout.status == "out",
            StorageInout.is_deleted.is_(False),
        )
        records = (await self.db.execute(stmt)).scalars().all()
        now = datetime.now(timezone.utc)
        for r in records:
            r.status = "returned"
            r.in_time = now
