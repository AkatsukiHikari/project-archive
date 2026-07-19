"""
利用申请 / 调阅篮 服务。

办理中(processing) → 办理完成(completed) / 已取消(cancelled)。
办结后，调阅篮条目即为利用登记明细（供"利用台账"统计）。
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone, date
from typing import Optional

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.error_code import ErrorCode
from app.common.exceptions.base import NotFoundException, ValidationException
from app.modules.iam.models.user import User
from app.modules.utilization.models.application import (
    UtilizationApplication,
    UtilizationItem,
)
from app.modules.utilization.schemas.application import (
    ApplicationCreate,
    ApplicationUpdate,
    ItemIn,
)


def _gen_reg_no(seq_today: int) -> str:
    return f"LY{date.today():%Y%m%d}{seq_today:03d}"


def _day_bound(s: str, *, end: bool) -> datetime:
    """'YYYY-MM-DD' → 当日 00:00:00 / 23:59:59 的 UTC datetime（避免与 timestamptz 列做字符串比较）。"""
    base = datetime.strptime(s[:10], "%Y-%m-%d")
    if end:
        base = base.replace(hour=23, minute=59, second=59)
    return base.replace(tzinfo=timezone.utc)


class ApplicationService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    # ── 登记 ──────────────────────────────────────────────────────

    async def create(
        self, data: ApplicationCreate, handler_id: uuid.UUID,
        tenant_id: Optional[uuid.UUID],
    ) -> UtilizationApplication:
        # 当日流水号
        start = datetime.combine(date.today(), datetime.min.time(), tzinfo=timezone.utc)
        cnt = (await self._db.execute(
            select(func.count()).select_from(UtilizationApplication)
            .where(UtilizationApplication.create_time >= start)
        )).scalar_one()
        app = UtilizationApplication(
            reg_no=_gen_reg_no(cnt + 1),
            applicant_name=data.applicant_name,
            id_card_no=data.id_card_no,
            gender=data.gender,
            phone=data.phone,
            organization=data.organization,
            avatar_key=data.avatar_key,
            purpose=data.purpose,
            use_type=data.use_type or "read",
            status="processing",
            handler_id=handler_id,
            tenant_id=tenant_id,
            create_by=handler_id,
        )
        self._db.add(app)
        await self._db.flush()
        await self._db.refresh(app)
        return app

    async def update(
        self, app_id: uuid.UUID, data: ApplicationUpdate, tenant_id: Optional[uuid.UUID],
    ) -> UtilizationApplication:
        app = await self._require(app_id, tenant_id)
        for field in ("applicant_name", "id_card_no", "gender", "phone", "organization", "purpose", "use_type"):
            v = getattr(data, field)
            if v is not None:
                setattr(app, field, v)
        await self._db.flush()
        return app

    async def set_status(
        self, app_id: uuid.UUID, status: str, tenant_id: Optional[uuid.UUID],
    ) -> UtilizationApplication:
        app = await self._require(app_id, tenant_id)
        app.status = status
        if status == "completed":
            app.completed_at = datetime.now(timezone.utc)
        await self._db.flush()
        return app

    # ── 列表（含调阅篮件数 + 经办人名） ───────────────────────────

    async def list(
        self, tenant_id: Optional[uuid.UUID], status: Optional[str], keyword: Optional[str],
        use_type: Optional[str] = None, source: Optional[str] = None,
    ) -> list[dict]:
        conds = [UtilizationApplication.is_deleted == False]  # noqa: E712
        if tenant_id is not None:
            conds.append(UtilizationApplication.tenant_id == tenant_id)
        if status:
            conds.append(UtilizationApplication.status == status)
        if use_type:
            conds.append(UtilizationApplication.use_type == use_type)
        if source:
            conds.append(UtilizationApplication.source == source)
        if keyword:
            kw = f"%{keyword}%"
            conds.append(or_(
                UtilizationApplication.applicant_name.ilike(kw),
                UtilizationApplication.reg_no.ilike(kw),
                UtilizationApplication.id_card_no.ilike(kw),
                UtilizationApplication.organization.ilike(kw),
                UtilizationApplication.access_code.ilike(kw),
            ))
        rows = (await self._db.execute(
            select(UtilizationApplication).where(and_(*conds))
            .order_by(UtilizationApplication.create_time.desc())
        )).scalars().all()

        app_ids = [a.id for a in rows]
        counts = await self._item_counts(app_ids)
        names = await self._handler_names([a.handler_id for a in rows if a.handler_id])

        out: list[dict] = []
        for a in rows:
            d = {c: getattr(a, c) for c in (
                "id", "reg_no", "applicant_name", "id_card_no", "gender", "phone",
                "organization", "avatar_key", "purpose", "use_type", "status",
                "handler_id", "completed_at", "create_time",
                "borrowed_at", "due_date", "returned_at", "copy_method", "copies",
                "fee", "delivered_at", "cert_no", "cert_content", "issued_at",
                "source", "access_code", "approved_at", "reject_reason",
            )}
            d["item_count"] = counts.get(a.id, 0)
            d["handler_name"] = names.get(a.handler_id)
            d["biz_status"] = a.biz_status
            out.append(d)
        return out

    async def detail(
        self, app_id: uuid.UUID, tenant_id: Optional[uuid.UUID],
    ) -> tuple[UtilizationApplication, list[UtilizationItem], int, Optional[str]]:
        app = await self._require(app_id, tenant_id)
        items = (await self._db.execute(
            select(UtilizationItem)
            .where(UtilizationItem.application_id == app_id, UtilizationItem.is_deleted == False)  # noqa: E712
            .order_by(UtilizationItem.create_time)
        )).scalars().all()
        names = await self._handler_names([app.handler_id] if app.handler_id else [])
        return app, list(items), len(items), names.get(app.handler_id)

    # ── 调阅篮 ────────────────────────────────────────────────────

    async def add_items(
        self, app_id: uuid.UUID, items: list[ItemIn], tenant_id: Optional[uuid.UUID],
    ) -> int:
        app = await self._require(app_id, tenant_id)
        if app.status != "processing":
            raise ValidationException(message="该利用申请已办结，无法继续加入调阅篮")
        existing = set((await self._db.execute(
            select(UtilizationItem.archive_id).where(UtilizationItem.application_id == app_id)
        )).scalars().all())
        added = 0
        for it in items:
            if it.archive_id in existing:
                continue  # 去重
            self._db.add(UtilizationItem(
                application_id=app_id, archive_id=it.archive_id,
                DH=it.DH, TM=it.TM, RZZ=it.RZZ, ND=it.ND, QZH=it.QZH,
                tenant_id=tenant_id, create_by=app.handler_id,
            ))
            existing.add(it.archive_id)
            added += 1
        await self._db.flush()
        return added

    async def remove_item(
        self, app_id: uuid.UUID, item_id: uuid.UUID, tenant_id: Optional[uuid.UUID],
    ) -> None:
        await self._require(app_id, tenant_id)
        item = (await self._db.execute(
            select(UtilizationItem).where(
                UtilizationItem.id == item_id, UtilizationItem.application_id == app_id
            )
        )).scalar_one_or_none()
        if item:
            await self._db.delete(item)
            await self._db.flush()

    # ── 借阅 / 复制 / 证明 办理动作 ────────────────────────────────

    async def lend(self, app_id, due, tenant_id, operator_id=None):
        app = await self._require(app_id, tenant_id)
        app.borrowed_at = datetime.now(timezone.utc)
        app.due_date = due
        app.returned_at = None
        await self._db.flush()

        # 借阅联动：为调阅篮内每件档案生成出库记录（档案保管 → 出入库记录）
        from app.modules.storage.services.inout_service import InoutService
        from app.modules.utilization.models.application import UtilizationItem

        items = (await self._db.execute(
            select(UtilizationItem).where(UtilizationItem.application_id == app_id)
        )).scalars().all()
        await InoutService(self._db).on_borrow_lend(
            app_id=app_id,
            borrower=app.applicant_name,
            items=[{"archive_id": it.archive_id, "DH": it.DH, "TM": it.TM} for it in items],
            due=due,
            user_id=operator_id,
            tenant_id=tenant_id,
        )
        await self._db.flush()
        return app

    async def renew(self, app_id, due, tenant_id):
        app = await self._require(app_id, tenant_id)
        app.due_date = due
        await self._db.flush()
        return app

    async def return_borrow(self, app_id, tenant_id):
        app = await self._require(app_id, tenant_id)
        now = datetime.now(timezone.utc)
        app.returned_at = now
        app.status = "completed"
        app.completed_at = now
        await self._db.flush()

        # 借阅联动：归还时回写对应出库记录为已归还
        from app.modules.storage.services.inout_service import InoutService
        await InoutService(self._db).on_borrow_return(app_id, tenant_id)
        await self._db.flush()
        return app

    async def process_copy(self, app_id, method, copies, fee, tenant_id):
        app = await self._require(app_id, tenant_id)
        now = datetime.now(timezone.utc)
        app.copy_method = method
        app.copies = copies
        app.fee = fee
        app.delivered_at = now
        app.status = "completed"
        app.completed_at = now
        await self._db.flush()
        return app

    async def issue_cert(self, app_id, content, tenant_id):
        app = await self._require(app_id, tenant_id)
        now = datetime.now(timezone.utc)
        start = datetime.combine(date.today(), datetime.min.time(), tzinfo=timezone.utc)
        seq = (await self._db.execute(
            select(func.count()).select_from(UtilizationApplication)
            .where(UtilizationApplication.issued_at >= start)
        )).scalar_one()
        app.cert_no = f"ZM{date.today():%Y%m%d}{seq + 1:03d}"
        app.cert_content = content
        app.issued_at = now
        app.status = "completed"
        app.completed_at = now
        await self._db.flush()
        return app

    # ── 利用台账（逐条明细：谁 查了 哪件档案） ────────────────────

    async def ledger(
        self, tenant_id: Optional[uuid.UUID], *,
        status: Optional[str] = None, use_type: Optional[str] = None,
        keyword: Optional[str] = None, date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> list[dict]:
        A = UtilizationApplication
        I = UtilizationItem
        conds = [I.is_deleted == False, A.is_deleted == False]  # noqa: E712
        if tenant_id is not None:
            conds.append(A.tenant_id == tenant_id)
        if status:
            conds.append(A.status == status)
        if use_type:
            conds.append(A.use_type == use_type)
        if keyword:
            kw = f"%{keyword}%"
            conds.append(or_(
                A.applicant_name.ilike(kw), A.reg_no.ilike(kw),
                A.organization.ilike(kw), I.DH.ilike(kw), I.TM.ilike(kw),
            ))
        if date_from:
            conds.append(A.create_time >= _day_bound(date_from, end=False))
        if date_to:
            conds.append(A.create_time <= _day_bound(date_to, end=True))

        stmt = (
            select(I, A, User.full_name, User.username)
            .join(A, I.application_id == A.id)
            .outerjoin(User, User.id == A.handler_id)
            .where(and_(*conds))
            .order_by(A.create_time.desc(), I.create_time)
            .limit(10000)
        )
        rows = (await self._db.execute(stmt)).all()
        out: list[dict] = []
        for item, app, full, uname in rows:
            used_at = app.completed_at or app.create_time
            out.append({
                "reg_no": app.reg_no,
                "applicant_name": app.applicant_name,
                "organization": app.organization,
                "use_type": app.use_type,
                "purpose": app.purpose,
                "archive_id": str(item.archive_id),
                "DH": item.DH,
                "TM": item.TM,
                "ND": item.ND,
                "handler_name": full or uname,
                "status": app.status,
                "used_at": used_at.isoformat() if used_at else None,
            })
        return out

    # ── 利用台账（统计报表：按期/目的/方式/门类） ────────────────

    async def ledger_stats(
        self, tenant_id: Optional[uuid.UUID], *,
        granularity: str = "month",
        date_from: Optional[str] = None, date_to: Optional[str] = None,
    ) -> dict:
        from app.modules.repository.models.archive import ArchiveStaging

        A = UtilizationApplication
        I = UtilizationItem
        conds = [I.is_deleted == False, A.is_deleted == False]  # noqa: E712
        if tenant_id is not None:
            conds.append(A.tenant_id == tenant_id)
        if date_from:
            conds.append(A.create_time >= _day_bound(date_from, end=False))
        if date_to:
            conds.append(A.create_time <= _day_bound(date_to, end=True))

        rows = (await self._db.execute(
            select(I, A, ArchiveStaging.category_id)
            .join(A, I.application_id == A.id)
            .outerjoin(ArchiveStaging, ArchiveStaging.id == I.archive_id)
            .where(and_(*conds))
        )).all()

        def period_key(dt) -> str:
            if not dt:
                return "未知"
            if granularity == "year":
                return f"{dt.year}"
            if granularity == "quarter":
                return f"{dt.year}-Q{(dt.month - 1) // 3 + 1}"
            return f"{dt.year}-{dt.month:02d}"

        by_period: dict[str, int] = {}
        by_purpose: dict[str, int] = {}
        by_use_type: dict[str, int] = {}
        by_category: dict[str, int] = {}
        app_ids: set = set()
        archive_ids: set = set()

        for item, app, category_id in rows:
            used_at = app.completed_at or app.create_time
            by_period[period_key(used_at)] = by_period.get(period_key(used_at), 0) + 1
            p = app.purpose or "未填写"
            by_purpose[p] = by_purpose.get(p, 0) + 1
            by_use_type[app.use_type] = by_use_type.get(app.use_type, 0) + 1
            ck = str(category_id) if category_id else "未分类"
            by_category[ck] = by_category.get(ck, 0) + 1
            app_ids.add(app.id)
            archive_ids.add(item.archive_id)

        def to_list(d: dict, key_name: str) -> list[dict]:
            return [{key_name: k, "count": v} for k, v in sorted(d.items(), key=lambda x: -x[1])]

        return {
            "summary": {
                "items": len(rows),                  # 利用件次
                "applications": len(app_ids),        # 利用人次（登记数）
                "archives": len(archive_ids),        # 涉及档案数
            },
            "by_period": sorted(
                [{"period": k, "count": v} for k, v in by_period.items()],
                key=lambda x: x["period"],
            ),
            "by_purpose": to_list(by_purpose, "name"),
            "by_use_type": to_list(by_use_type, "name"),
            "by_category": to_list(by_category, "category_id"),
        }

    # ── 内部 ──────────────────────────────────────────────────────

    async def _require(
        self, app_id: uuid.UUID, tenant_id: Optional[uuid.UUID],
    ) -> UtilizationApplication:
        conds = [UtilizationApplication.id == app_id, UtilizationApplication.is_deleted == False]  # noqa: E712
        if tenant_id is not None:
            conds.append(UtilizationApplication.tenant_id == tenant_id)
        app = (await self._db.execute(select(UtilizationApplication).where(and_(*conds)))).scalar_one_or_none()
        if not app:
            raise NotFoundException(code=ErrorCode.NOT_FOUND, message="利用申请不存在")
        return app

    async def _item_counts(self, app_ids: list[uuid.UUID]) -> dict[uuid.UUID, int]:
        if not app_ids:
            return {}
        rows = (await self._db.execute(
            select(UtilizationItem.application_id, func.count())
            .where(UtilizationItem.application_id.in_(app_ids), UtilizationItem.is_deleted == False)  # noqa: E712
            .group_by(UtilizationItem.application_id)
        )).all()
        return {aid: n for aid, n in rows}

    async def _handler_names(self, ids: list[uuid.UUID]) -> dict[uuid.UUID, str]:
        ids = [i for i in ids if i]
        if not ids:
            return {}
        rows = (await self._db.execute(
            select(User.id, User.full_name, User.username).where(User.id.in_(ids))
        )).all()
        return {uid: (full or uname) for uid, full, uname in rows}
