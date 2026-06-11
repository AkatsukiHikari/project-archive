"""四性检测 API。挂载前缀 /preservation。

检测项目录  GET /check-items
检测方案    GET/POST /schemes, GET/PUT/DELETE /schemes/{id}, POST /schemes/{id}/default
检测运行    POST /runs, GET /runs, GET /runs/{id}, POST /runs/{id}/results/{item_id}/decide
"""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.response import ResponseModel, success
from app.infra.db.session import get_db
from app.modules.iam.api.dependencies import get_current_user
from app.modules.iam.models.user import User
from app.modules.preservation.schemas.run import (
    BatchDetail, BatchOut, BatchRunRequest, ManualDecision, ResultItemOut, RunDetail, RunOut, RunRequest,
)
from app.modules.preservation.schemas.scheme import (
    CheckItemOut, SchemeCreate, SchemeDetail, SchemeItemOut, SchemeOut, SchemeUpdate,
)
from app.modules.preservation.services.scheme_service import PreservationService

router = APIRouter(prefix="/preservation", tags=["四性检测"])


# ── 检测项目录 ────────────────────────────────────────────────────────────────

@router.get("/check-items", response_model=ResponseModel[list[CheckItemOut]])
async def list_check_items(db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    items = await PreservationService(db).list_check_items()
    return success([CheckItemOut.model_validate(i).model_dump(mode="json") for i in items])


# ── 检测方案 ──────────────────────────────────────────────────────────────────

@router.get("/schemes", response_model=ResponseModel[list[SchemeOut]])
async def list_schemes(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    rows = await PreservationService(db).list_schemes(current_user.tenant_id)
    return success([SchemeOut.model_validate(r).model_dump(mode="json") for r in rows])


@router.post("/schemes", response_model=ResponseModel[SchemeOut])
async def create_scheme(body: SchemeCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    svc = PreservationService(db)
    s = await svc.create_scheme(body, current_user.tenant_id)
    await db.commit()
    out = SchemeOut.model_validate(s).model_dump(mode="json")
    out["item_count"] = len(body.items)
    return success(out)


@router.get("/schemes/{scheme_id}", response_model=ResponseModel[SchemeDetail])
async def get_scheme(scheme_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    svc = PreservationService(db)
    s = await svc.get_scheme(scheme_id, current_user.tenant_id)
    items = await svc.scheme_items_enriched(scheme_id)
    data = SchemeOut.model_validate(s).model_dump(mode="json")
    data["item_count"] = len(items)
    data["items"] = [SchemeItemOut.model_validate(i).model_dump(mode="json") for i in items]
    return success(data)


@router.put("/schemes/{scheme_id}", response_model=ResponseModel[SchemeOut])
async def update_scheme(scheme_id: uuid.UUID, body: SchemeUpdate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    svc = PreservationService(db)
    s = await svc.update_scheme(scheme_id, body, current_user.tenant_id)
    await db.commit()
    return success(SchemeOut.model_validate(s).model_dump(mode="json"))


@router.post("/schemes/{scheme_id}/default", response_model=ResponseModel[SchemeOut])
async def set_default(scheme_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    svc = PreservationService(db)
    s = await svc.set_default(scheme_id, current_user.tenant_id)
    await db.commit()
    return success(SchemeOut.model_validate(s).model_dump(mode="json"))


@router.delete("/schemes/{scheme_id}", response_model=ResponseModel[None])
async def delete_scheme(scheme_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    svc = PreservationService(db)
    await svc.delete_scheme(scheme_id, current_user.tenant_id)
    await db.commit()
    return success()


# ── 检测运行 ──────────────────────────────────────────────────────────────────

@router.post("/runs", response_model=ResponseModel[BatchOut])
async def run_detection(body: RunRequest, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    """单件检测：也生成一个批次（含 1 件）。"""
    svc = PreservationService(db)
    batch = await svc.run_single(body.archive_id, body.scheme_id, current_user.id, current_user.tenant_id)
    await db.commit()
    return success(BatchOut.model_validate(batch).model_dump(mode="json"))


@router.post("/runs/batch", response_model=ResponseModel[BatchOut])
async def run_batch(body: BatchRunRequest, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    svc = PreservationService(db)
    batch = await svc.run_batch(
        scheme_id=body.scheme_id, fonds_id=body.fonds_id, catalog_id=body.catalog_id,
        category_id=body.category_id, nd=body.ND, operator_id=current_user.id, tenant_id=current_user.tenant_id,
    )
    await db.commit()
    return success(BatchOut.model_validate(batch).model_dump(mode="json"))


@router.get("/batches", response_model=ResponseModel[list[BatchOut]])
async def list_batches(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    batches = await PreservationService(db).list_batches(current_user.tenant_id)
    return success([BatchOut.model_validate(b).model_dump(mode="json") for b in batches])


@router.get("/batches/{batch_id}", response_model=ResponseModel[BatchDetail])
async def get_batch(batch_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    svc = PreservationService(db)
    batch, runs = await svc.get_batch(batch_id, current_user.tenant_id)
    data = BatchOut.model_validate(batch).model_dump(mode="json")
    data["runs"] = [RunOut.model_validate(r).model_dump(mode="json") for r in runs]
    return success(data)


@router.get("/runs/{run_id}", response_model=ResponseModel[RunDetail])
async def get_run(run_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    svc = PreservationService(db)
    run, results = await svc.get_run(run_id, current_user.tenant_id)
    data = RunOut.model_validate(run).model_dump(mode="json")
    data["results"] = [ResultItemOut.model_validate(r).model_dump(mode="json") for r in results]
    return success(data)


@router.post("/runs/{run_id}/results/{item_id}/decide", response_model=ResponseModel[RunOut])
async def decide_manual(
    run_id: uuid.UUID, item_id: uuid.UUID, body: ManualDecision,
    db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user),
):
    svc = PreservationService(db)
    run = await svc.decide_manual(run_id, item_id, body.result, body.message, current_user.id, current_user.tenant_id)
    await db.commit()
    return success(RunOut.model_validate(run).model_dump(mode="json"))
