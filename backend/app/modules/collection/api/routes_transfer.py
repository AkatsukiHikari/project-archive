"""
归档移交 / 接收登记 / 收集台账 API。

挂载前缀： /collection/transfer

归档计划   POST/GET /plans, PUT /plans/{id}
移交单     POST/GET /batches, GET /batches/{id}, PUT /batches/{id}/entries,
           POST /batches/{id}/submit, POST /batches/{id}/precheck-preview
接收登记   POST /receive/{id}/precheck | /accept | /return
收集台账   GET /ledger
"""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.response import ResponseModel, success
from app.core.security.permissions import require_permissions
from app.infra.db.session import get_db
from app.modules.collection.schemas.transfer import (
    LedgerSummary,
    PrecheckResponse,
    ReceiveAcceptRequest,
    ReceiveReturnRequest,
    TransferBatchCreate,
    TransferBatchDetail,
    TransferBatchOut,
    TransferEntriesReplace,
    TransferEntryOut,
    TransferPlanCreate,
    TransferPlanOut,
    TransferPlanUpdate,
)
from app.modules.collection.services.ledger_service import LedgerService
from app.modules.collection.services.receive_service import ReceiveService
from app.modules.collection.services.transfer_service import TransferService
from app.modules.iam.api.dependencies import get_current_user
from app.modules.iam.models.user import User

router = APIRouter(prefix="/collection/transfer", tags=["归档移交"])


def _batch_out(batch) -> dict:
    return TransferBatchOut.model_validate(batch).model_dump(mode="json")


# ── 归档计划 ──────────────────────────────────────────────────────────────────

@router.post("/plans", response_model=ResponseModel[TransferPlanOut])
async def create_plan(
    body: TransferPlanCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("collection:create")),
):
    svc = TransferService(db)
    plan = await svc.create_plan(body, current_user.id, current_user.tenant_id)
    await db.commit()
    return success(TransferPlanOut.model_validate(plan).model_dump(mode="json"))


@router.get("/plans", response_model=ResponseModel[list[TransferPlanOut]])
async def list_plans(
    year: Optional[int] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = TransferService(db)
    plans = await svc.list_plans(current_user.tenant_id, year=year, skip=skip, limit=limit)
    return success([TransferPlanOut.model_validate(p).model_dump(mode="json") for p in plans])


@router.put("/plans/{plan_id}", response_model=ResponseModel[TransferPlanOut])
async def update_plan(
    plan_id: uuid.UUID,
    body: TransferPlanUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("collection:create")),
):
    svc = TransferService(db)
    plan = await svc.update_plan(plan_id, body, current_user.tenant_id)
    await db.commit()
    return success(TransferPlanOut.model_validate(plan).model_dump(mode="json"))


# ── 移交单 ────────────────────────────────────────────────────────────────────

@router.post("/batches", response_model=ResponseModel[TransferBatchOut])
async def create_batch(
    body: TransferBatchCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("collection:create")),
):
    svc = TransferService(db)
    batch = await svc.create_batch(body, current_user.id, current_user.tenant_id)
    await db.commit()
    return success(_batch_out(batch))


@router.get("/batches", response_model=ResponseModel[list[TransferBatchOut]])
async def list_batches(
    status: Optional[str] = Query(None),
    year: Optional[int] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = TransferService(db)
    batches = await svc.list_batches(
        current_user.tenant_id, status=status, year=year, skip=skip, limit=limit
    )
    return success([_batch_out(b) for b in batches])


@router.get("/batches/{batch_id}", response_model=ResponseModel[TransferBatchDetail])
async def get_batch(
    batch_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = TransferService(db)
    batch, entries = await svc.get_batch(batch_id, current_user.tenant_id)
    data = _batch_out(batch)
    data["entries"] = [
        TransferEntryOut.model_validate(e).model_dump(mode="json") for e in entries
    ]
    return success(data)


@router.put("/batches/{batch_id}/entries", response_model=ResponseModel[TransferBatchOut])
async def replace_entries(
    batch_id: uuid.UUID,
    body: TransferEntriesReplace,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("collection:create")),
):
    svc = TransferService(db)
    batch = await svc.replace_entries(batch_id, body.entries, current_user.tenant_id)
    await db.commit()
    return success(_batch_out(batch))


@router.post("/batches/{batch_id}/submit", response_model=ResponseModel[TransferBatchOut])
async def submit_batch(
    batch_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("collection:create")),
):
    svc = TransferService(db)
    batch = await svc.submit_batch(batch_id, current_user.tenant_id)
    await db.commit()
    return success(_batch_out(batch))


@router.post(
    "/batches/{batch_id}/precheck-preview",
    response_model=ResponseModel[PrecheckResponse],
)
async def precheck_preview(
    batch_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """四性预检预演（不落库），供移交单位自检。"""
    svc = TransferService(db)
    result = await svc.preview_precheck(batch_id, current_user.tenant_id)
    return success(_precheck_payload(result))


# ── 接收登记 ──────────────────────────────────────────────────────────────────

@router.post(
    "/receive/{batch_id}/precheck",
    response_model=ResponseModel[PrecheckResponse],
)
async def receive_precheck(
    batch_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("collection:review")),
):
    svc = ReceiveService(db)
    _, result = await svc.precheck(batch_id, current_user.id, current_user.tenant_id)
    await db.commit()
    return success(_precheck_payload(result))


@router.post("/receive/{batch_id}/accept", response_model=ResponseModel[TransferBatchOut])
async def receive_accept(
    batch_id: uuid.UUID,
    body: ReceiveAcceptRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("collection:review")),
):
    svc = ReceiveService(db)
    batch = await svc.accept(
        batch_id, current_user.id, current_user.tenant_id,
        catalog_id=body.catalog_id, force=body.force,
    )
    await db.commit()
    return success(_batch_out(batch))


@router.post("/receive/{batch_id}/return", response_model=ResponseModel[TransferBatchOut])
async def receive_return(
    batch_id: uuid.UUID,
    body: ReceiveReturnRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("collection:review")),
):
    svc = ReceiveService(db)
    batch = await svc.return_batch(
        batch_id, current_user.id, current_user.tenant_id, body.return_reason
    )
    await db.commit()
    return success(_batch_out(batch))


# ── 收集台账 / 催交看板 ───────────────────────────────────────────────────────

@router.get("/ledger", response_model=ResponseModel[LedgerSummary])
async def get_ledger(
    year: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = LedgerService(db)
    summary = await svc.build(current_user.tenant_id, year=year)
    return success(summary.model_dump(mode="json"))


# ── 内部 ──────────────────────────────────────────────────────────────────────

def _precheck_payload(result) -> dict:
    detail = result.to_detail()
    detail["entries"] = [
        {"row_no": e.row_no, "status": e.status, "issues": e.issues}
        for e in result.entries
    ]
    return detail
