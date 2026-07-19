"""自助查询机（kiosk）通道 + 利用服务中心动作。

- 民众在自助机检索公开档案 → 提交「申请查看」（生成申请码，状态 pending）
- 工作人员在利用服务中心 同意(→processing)/拒绝(→rejected)/转办(留痕)/代办结
- 批准后民众凭申请码在任意自助机在线阅览（仅限申请内档案；办结/取消后失效）
"""

from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timezone, date, time as dtime
from typing import Optional

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions.base import NotFoundException, ValidationException
from app.modules.audit.repositories.audit_repository import SQLAlchemyAuditRepository
from app.modules.audit.schemas import AuditLogCreate
from app.modules.audit.services.audit_service import AuditService
from app.modules.iam.models.user import User
from app.modules.utilization.models.application import (
    UtilizationApplication,
    UtilizationItem,
)
from app.modules.utilization.schemas.application import ItemIn
from app.modules.utilization.services.application_service import _gen_reg_no

AUDIT_MODULE = "utilization"

# 申请码有效状态：待审批可查进度，办理中可阅览；办结/取消/拒绝后码即失效
CODE_ACTIVE_STATUSES = ("pending", "processing")


async def _audit(
    db: AsyncSession, user_id: Optional[uuid.UUID], tenant_id: Optional[uuid.UUID],
    action: str, details: dict,
) -> None:
    await AuditService(SQLAlchemyAuditRepository(db)).create_audit_log(
        AuditLogCreate(
            user_id=user_id, tenant_id=tenant_id,
            action=action, module=AUDIT_MODULE, details=details,
        )
    )


async def _gen_access_code(db: AsyncSession) -> str:
    """6 位数字申请码，在有效申请中唯一。"""
    for _ in range(20):
        code = f"{secrets.randbelow(1000000):06d}"
        exists = (
            await db.execute(
                select(UtilizationApplication.id).where(
                    UtilizationApplication.access_code == code,
                    UtilizationApplication.status.in_(CODE_ACTIVE_STATUSES),
                    UtilizationApplication.is_deleted.is_(False),
                ).limit(1)
            )
        ).scalar_one_or_none()
        if exists is None:
            return code
    raise ValidationException(message="申请码生成失败，请重试")


# ── 自助机：提交申请 ───────────────────────────────────────────────────────────
async def kiosk_create(
    db: AsyncSession,
    applicant_name: str,
    phone: str,
    id_card_no: Optional[str],
    purpose: Optional[str],
    items: list[ItemIn],
    device_user_id: uuid.UUID,
    tenant_id: Optional[uuid.UUID],
) -> dict:
    if not items:
        raise ValidationException(message="请先选择要申请查看的档案")

    start = datetime.combine(date.today(), dtime.min, tzinfo=timezone.utc)
    cnt = (
        await db.execute(
            select(func.count()).select_from(UtilizationApplication)
            .where(UtilizationApplication.create_time >= start)
        )
    ).scalar_one()

    code = await _gen_access_code(db)
    app = UtilizationApplication(
        reg_no=_gen_reg_no(cnt + 1),
        applicant_name=applicant_name.strip(),
        phone=phone.strip(),
        id_card_no=(id_card_no or "").strip() or None,
        purpose=(purpose or "").strip() or None,
        use_type="read",
        status="pending",
        source="kiosk",
        access_code=code,
        tenant_id=tenant_id,
        create_by=device_user_id,
    )
    db.add(app)
    await db.flush()
    for it in items:
        db.add(
            UtilizationItem(
                application_id=app.id, archive_id=it.archive_id,
                DH=it.DH, TM=it.TM, RZZ=it.RZZ, ND=it.ND, QZH=it.QZH,
                tenant_id=tenant_id, create_by=device_user_id,
            )
        )
    await db.commit()
    return {"reg_no": app.reg_no, "access_code": code, "id": str(app.id)}


# ── 自助机：凭码取回状态 ───────────────────────────────────────────────────────
async def kiosk_status(db: AsyncSession, code: str, tenant_id: Optional[uuid.UUID]) -> dict:
    app = await _by_code(db, code, tenant_id, allow_inactive=True)
    if app is None:
        return {"ok": False, "reason": "申请码不存在或已失效"}
    items = (
        await db.execute(
            select(UtilizationItem).where(
                UtilizationItem.application_id == app.id,
                UtilizationItem.is_deleted.is_(False),
            ).order_by(UtilizationItem.create_time)
        )
    ).scalars().all()
    return {
        "ok": True,
        "reg_no": app.reg_no,
        "applicant_name": app.applicant_name,
        "status": app.status,
        "reject_reason": app.reject_reason,
        "create_time": app.create_time.isoformat() if app.create_time else None,
        # 仅办理中（已批准）可在自助机阅览原文
        "viewable": app.status == "processing",
        "items": [
            {
                "archive_id": str(i.archive_id),
                "DH": i.DH, "TM": i.TM, "RZZ": i.RZZ, "ND": i.ND, "QZH": i.QZH,
            }
            for i in items
        ],
    }


async def _by_code(
    db: AsyncSession, code: str, tenant_id: Optional[uuid.UUID], allow_inactive: bool = False,
) -> Optional[UtilizationApplication]:
    conds = [
        UtilizationApplication.access_code == (code or "").strip(),
        UtilizationApplication.source == "kiosk",
        UtilizationApplication.is_deleted.is_(False),
    ]
    if not allow_inactive:
        conds.append(UtilizationApplication.status.in_(CODE_ACTIVE_STATUSES))
    if tenant_id:
        conds.append(UtilizationApplication.tenant_id == tenant_id)
    return (
        await db.execute(
            select(UtilizationApplication).where(and_(*conds))
            .order_by(UtilizationApplication.create_time.desc()).limit(1)
        )
    ).scalars().first()


# ── 自助机：批准后取原文（服务端校验：码有效 + 档案在申请内） ─────────────────
async def kiosk_attachments(
    db: AsyncSession, code: str, archive_id: uuid.UUID, tenant_id: Optional[uuid.UUID],
) -> list[dict]:
    app = await _by_code(db, code, tenant_id)
    if app is None or app.status != "processing":
        raise ValidationException(message="申请未批准或已失效，无法查看原文")
    in_app = (
        await db.execute(
            select(UtilizationItem.id).where(
                UtilizationItem.application_id == app.id,
                UtilizationItem.archive_id == archive_id,
                UtilizationItem.is_deleted.is_(False),
            ).limit(1)
        )
    ).scalar_one_or_none()
    if in_app is None:
        raise ValidationException(message="该档案不在本次申请范围内")

    from app.infra.storage.factory import storage
    from app.modules.repository.models.archive import ArchiveAttachment
    from app.modules.repository.schemas.archive import AttachmentRead

    rows = (
        await db.execute(
            select(ArchiveAttachment).where(
                ArchiveAttachment.archive_id == archive_id,
                ArchiveAttachment.is_deleted.is_(False),
            ).order_by(ArchiveAttachment.is_primary.desc(), ArchiveAttachment.sort_order)
        )
    ).scalars().all()
    out: list[dict] = []
    for a in rows:
        try:
            url = storage.get_presigned_url(a.storage_key, a.storage_bucket, expires_seconds=1800)
        except Exception:  # noqa: BLE001 — 单附件取链失败不阻断其余
            url = None
        item = AttachmentRead.model_validate(a).model_dump(mode="json")
        item["url"] = url
        out.append(item)
    return out


# ── 服务中心：审批 / 转办 ──────────────────────────────────────────────────────
async def _require_app(
    db: AsyncSession, app_id: uuid.UUID, tenant_id: Optional[uuid.UUID],
) -> UtilizationApplication:
    conds = [
        UtilizationApplication.id == app_id,
        UtilizationApplication.is_deleted.is_(False),
    ]
    if tenant_id:
        conds.append(UtilizationApplication.tenant_id == tenant_id)
    app = (await db.execute(select(UtilizationApplication).where(and_(*conds)))).scalars().first()
    if app is None:
        raise NotFoundException(message="利用申请不存在")
    return app


async def approve(
    db: AsyncSession, app_id: uuid.UUID, operator: User,
) -> UtilizationApplication:
    app = await _require_app(db, app_id, operator.tenant_id)
    if app.status != "pending":
        raise ValidationException(message="仅待审批的申请可批准")
    app.status = "processing"
    app.approved_by = operator.id
    app.approved_at = datetime.now(timezone.utc)
    app.handler_id = app.handler_id or operator.id
    await _audit(db, operator.id, operator.tenant_id, "UTIL_KIOSK_APPROVE",
                 {"reg_no": app.reg_no, "applicant": app.applicant_name})
    await db.commit()
    return app


async def reject(
    db: AsyncSession, app_id: uuid.UUID, reason: str, operator: User,
) -> UtilizationApplication:
    app = await _require_app(db, app_id, operator.tenant_id)
    if app.status != "pending":
        raise ValidationException(message="仅待审批的申请可拒绝")
    app.status = "rejected"
    app.reject_reason = (reason or "").strip() or None
    app.approved_by = operator.id
    app.approved_at = datetime.now(timezone.utc)
    await _audit(db, operator.id, operator.tenant_id, "UTIL_KIOSK_REJECT",
                 {"reg_no": app.reg_no, "applicant": app.applicant_name, "reason": app.reject_reason})
    await db.commit()
    return app


async def transfer(
    db: AsyncSession, app_id: uuid.UUID, new_handler_id: uuid.UUID, operator: User,
) -> UtilizationApplication:
    """转办：改经办人，审计留痕（谁、从谁、转给谁、何时）。"""
    app = await _require_app(db, app_id, operator.tenant_id)
    if app.status not in ("processing", "pending"):
        raise ValidationException(message="仅待审批/办理中的申请可转办")

    users = (
        await db.execute(
            select(User).where(User.id.in_([u for u in (app.handler_id, new_handler_id) if u]))
        )
    ).scalars().all()
    names = {u.id: (u.full_name or u.username) for u in users}
    if new_handler_id not in names:
        raise ValidationException(message="目标经办人不存在")

    old_id = app.handler_id
    app.handler_id = new_handler_id
    await _audit(db, operator.id, operator.tenant_id, "UTIL_APP_TRANSFER", {
        "reg_no": app.reg_no,
        "applicant": app.applicant_name,
        "from_handler_id": str(old_id) if old_id else None,
        "from_handler": names.get(old_id),
        "to_handler_id": str(new_handler_id),
        "to_handler": names.get(new_handler_id),
    })
    await db.commit()
    return app


# ── 服务中心：今日概览 ─────────────────────────────────────────────────────────
async def center_summary(db: AsyncSession, tenant_id: Optional[uuid.UUID]) -> dict:
    start = datetime.combine(date.today(), dtime.min, tzinfo=timezone.utc)
    base = [UtilizationApplication.is_deleted.is_(False)]
    if tenant_id:
        base.append(UtilizationApplication.tenant_id == tenant_id)

    async def _count(*extra) -> int:
        return (
            await db.execute(
                select(func.count()).select_from(UtilizationApplication).where(and_(*base, *extra))
            )
        ).scalar_one()

    return {
        "today_total": await _count(UtilizationApplication.create_time >= start),
        "processing": await _count(UtilizationApplication.status == "processing"),
        "pending": await _count(UtilizationApplication.status == "pending"),
        "today_completed": await _count(
            UtilizationApplication.status == "completed",
            UtilizationApplication.completed_at >= start,
        ),
        "kiosk_today": await _count(
            UtilizationApplication.source == "kiosk",
            UtilizationApplication.create_time >= start,
        ),
    }
