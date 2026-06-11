"""
利用申请 / 调阅篮 API。挂载前缀 /utilization。

登记      POST/GET /applications, GET /applications/{id}, PUT /applications/{id}
办理状态  POST /applications/{id}/complete | /cancel
调阅篮    POST /applications/{id}/items, DELETE /applications/{id}/items/{item_id}
"""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.response import ResponseModel, success
from app.infra.db.session import get_db
from app.modules.iam.api.dependencies import get_current_user
from app.modules.iam.models.user import User
from app.modules.utilization.schemas.application import (
    ApplicationCreate,
    ApplicationDetail,
    ApplicationOut,
    ApplicationUpdate,
    BorrowLendRequest,
    BorrowRenewRequest,
    CertIssueRequest,
    CopyProcessRequest,
    ItemOut,
    ItemsAdd,
)
from app.modules.utilization.services.application_service import ApplicationService

router = APIRouter(prefix="/utilization", tags=["档案利用"])


@router.get("/ledger/stats", response_model=ResponseModel[dict])
async def utilization_ledger_stats(
    granularity: str = Query(default="month"),
    date_from: Optional[str] = Query(default=None),
    date_to: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """利用台账（统计报表）：按月/季/年的利用趋势 + 目的/方式/门类分布。"""
    svc = ApplicationService(db)
    data = await svc.ledger_stats(
        current_user.tenant_id, granularity=granularity,
        date_from=date_from, date_to=date_to,
    )
    return success(data)


@router.get("/ledger", response_model=ResponseModel[list[dict]])
async def utilization_ledger(
    status: Optional[str] = Query(default=None),
    use_type: Optional[str] = Query(default=None),
    keyword: Optional[str] = Query(default=None),
    date_from: Optional[str] = Query(default=None),
    date_to: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """利用台账：逐条明细（谁、何时、以何方式/目的、查阅了哪件档案），可筛选/导出/打印。"""
    svc = ApplicationService(db)
    rows = await svc.ledger(
        current_user.tenant_id, status=status, use_type=use_type,
        keyword=keyword, date_from=date_from, date_to=date_to,
    )
    return success(rows)


@router.post("/applications", response_model=ResponseModel[ApplicationOut])
async def create_application(
    body: ApplicationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = ApplicationService(db)
    app = await svc.create(body, current_user.id, current_user.tenant_id)
    await db.commit()
    return success(ApplicationOut.model_validate(app).model_dump(mode="json"))


@router.get("/applications", response_model=ResponseModel[list[ApplicationOut]])
async def list_applications(
    status: Optional[str] = Query(default=None),
    use_type: Optional[str] = Query(default=None),
    keyword: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = ApplicationService(db)
    rows = await svc.list(current_user.tenant_id, status=status or None, keyword=keyword, use_type=use_type or None)
    return success([ApplicationOut.model_validate(r).model_dump(mode="json") for r in rows])


@router.get("/applications/{app_id}", response_model=ResponseModel[ApplicationDetail])
async def get_application(
    app_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = ApplicationService(db)
    app, items, count, handler_name = await svc.detail(app_id, current_user.tenant_id)
    data = ApplicationOut.model_validate(app).model_dump(mode="json")
    data["item_count"] = count
    data["handler_name"] = handler_name
    data["items"] = [ItemOut.model_validate(i).model_dump(mode="json") for i in items]
    return success(data)


@router.put("/applications/{app_id}", response_model=ResponseModel[ApplicationOut])
async def update_application(
    app_id: uuid.UUID,
    body: ApplicationUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = ApplicationService(db)
    app = await svc.update(app_id, body, current_user.tenant_id)
    await db.commit()
    return success(ApplicationOut.model_validate(app).model_dump(mode="json"))


@router.post("/applications/{app_id}/complete", response_model=ResponseModel[ApplicationOut])
async def complete_application(
    app_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = ApplicationService(db)
    app = await svc.set_status(app_id, "completed", current_user.tenant_id)
    await db.commit()
    return success(ApplicationOut.model_validate(app).model_dump(mode="json"))


@router.post("/applications/{app_id}/cancel", response_model=ResponseModel[ApplicationOut])
async def cancel_application(
    app_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = ApplicationService(db)
    app = await svc.set_status(app_id, "cancelled", current_user.tenant_id)
    await db.commit()
    return success(ApplicationOut.model_validate(app).model_dump(mode="json"))


@router.post("/applications/{app_id}/items", response_model=ResponseModel[dict])
async def add_items(
    app_id: uuid.UUID,
    body: ItemsAdd,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = ApplicationService(db)
    added = await svc.add_items(app_id, body.items, current_user.tenant_id)
    await db.commit()
    return success({"added": added})


@router.delete("/applications/{app_id}/items/{item_id}", response_model=ResponseModel[None])
async def remove_item(
    app_id: uuid.UUID,
    item_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = ApplicationService(db)
    await svc.remove_item(app_id, item_id, current_user.tenant_id)
    await db.commit()
    return success()


# ── 借阅 / 复制 / 证明 办理动作 ──────────────────────────────────────────────

def _out(app) -> dict:
    return ApplicationOut.model_validate(app).model_dump(mode="json")


@router.post("/applications/{app_id}/lend", response_model=ResponseModel[ApplicationOut])
async def lend(app_id: uuid.UUID, body: BorrowLendRequest, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    app = await ApplicationService(db).lend(app_id, body.due_date, current_user.tenant_id)
    await db.commit()
    return success(_out(app))


@router.post("/applications/{app_id}/renew", response_model=ResponseModel[ApplicationOut])
async def renew(app_id: uuid.UUID, body: BorrowRenewRequest, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    app = await ApplicationService(db).renew(app_id, body.due_date, current_user.tenant_id)
    await db.commit()
    return success(_out(app))


@router.post("/applications/{app_id}/return", response_model=ResponseModel[ApplicationOut])
async def return_borrow(app_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    app = await ApplicationService(db).return_borrow(app_id, current_user.tenant_id)
    await db.commit()
    return success(_out(app))


@router.post("/applications/{app_id}/copy", response_model=ResponseModel[ApplicationOut])
async def process_copy(app_id: uuid.UUID, body: CopyProcessRequest, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    app = await ApplicationService(db).process_copy(app_id, body.copy_method, body.copies, body.fee, current_user.tenant_id)
    await db.commit()
    return success(_out(app))


@router.post("/applications/{app_id}/issue-cert", response_model=ResponseModel[ApplicationOut])
async def issue_cert(app_id: uuid.UUID, body: CertIssueRequest, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    app = await ApplicationService(db).issue_cert(app_id, body.cert_content, current_user.tenant_id)
    await db.commit()
    return success(_out(app))
