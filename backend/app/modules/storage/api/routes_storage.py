"""档案保管 API。

挂载前缀： /storage

库房   GET/POST /vaults, GET/PUT/DELETE /vaults/{id}
出入库 GET/POST /inout, POST /inout/{id}/return
台账   GET /ledger
"""

import uuid
from typing import Optional

from fastapi import APIRouter, Body, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.response import ResponseModel, success
from app.infra.db.session import get_db
from app.modules.iam.api.dependencies import get_current_user
from app.modules.iam.models.user import User
from app.modules.storage.schemas.vault import (InoutCreate, InoutOut,
                                               VaultCreate, VaultDetail,
                                               VaultOut, VaultUpdate)
from app.modules.storage.services.inout_service import InoutService
from app.modules.storage.services.vault_service import VaultService

router = APIRouter(prefix="/storage", tags=["档案保管"])


# ── 库房 ──────────────────────────────────────────────────────────────────────


@router.get("/vaults", response_model=ResponseModel[list[VaultOut]])
async def list_vaults(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = VaultService(db)
    vaults = await svc.list_vaults(current_user.tenant_id)
    return success([VaultOut.model_validate(v).model_dump(mode="json") for v in vaults])


@router.get("/vaults/{vault_id}", response_model=ResponseModel[VaultDetail])
async def get_vault(
    vault_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = VaultService(db)
    data = await svc.get_vault(vault_id, current_user.tenant_id)
    return success(VaultDetail.model_validate(data).model_dump(mode="json"))


@router.post("/vaults", response_model=ResponseModel[VaultOut])
async def create_vault(
    body: VaultCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = VaultService(db)
    vault = await svc.create_vault(body, current_user.tenant_id)
    await db.commit()
    data = svc._vault_dict(vault, 0)
    return success(VaultOut.model_validate(data).model_dump(mode="json"))


@router.put("/vaults/{vault_id}", response_model=ResponseModel[VaultOut])
async def update_vault(
    vault_id: uuid.UUID,
    body: VaultUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = VaultService(db)
    vault = await svc.update_vault(vault_id, body, current_user.tenant_id)
    await db.commit()
    used = (await svc._vault_used_map(current_user.tenant_id)).get(vault.id, 0)
    data = svc._vault_dict(vault, used)
    return success(VaultOut.model_validate(data).model_dump(mode="json"))


# ── 架位管理 ──────────────────────────────────────────────────────────────────


@router.get("/shelves/{shelf_id}", response_model=ResponseModel[dict])
async def get_shelf(
    shelf_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = VaultService(db)
    return success(await svc.shelf_detail(shelf_id, current_user.tenant_id))


@router.put("/shelves/{shelf_id}", response_model=ResponseModel[None])
async def update_shelf(
    shelf_id: uuid.UUID,
    body: dict = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = VaultService(db)
    await svc.update_shelf(
        shelf_id,
        current_user.tenant_id,
        capacity=body.get("capacity"),
        label=body.get("label"),
    )
    await db.commit()
    return success(None)


@router.post("/shelves/{shelf_id}/assign", response_model=ResponseModel[dict])
async def assign_to_shelf(
    shelf_id: uuid.UUID,
    body: dict = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """上架：把档案放到该架位。body: {archive_ids: [...]}"""
    svc = VaultService(db)
    ids = [uuid.UUID(x) for x in body.get("archive_ids", [])]
    n = await svc.assign_archives(shelf_id, ids, current_user.tenant_id)
    await db.commit()
    return success({"assigned": n})


@router.get("/unshelved", response_model=ResponseModel[list[dict]])
async def list_unshelved(
    keyword: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """待上架档案（正式库中未关联架位的）。"""
    svc = VaultService(db)
    rows = await svc.list_unshelved(
        current_user.tenant_id, keyword=keyword, limit=limit
    )
    return success([{**r, "id": str(r["id"])} for r in rows])


@router.post("/shelves/unassign", response_model=ResponseModel[dict])
async def unassign_from_shelf(
    body: dict = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """下架：清除档案的架位关联。body: {archive_ids: [...]}"""
    svc = VaultService(db)
    ids = [uuid.UUID(x) for x in body.get("archive_ids", [])]
    n = await svc.unassign_archives(ids, current_user.tenant_id)
    await db.commit()
    return success({"unassigned": n})


@router.delete("/vaults/{vault_id}", response_model=ResponseModel[None])
async def delete_vault(
    vault_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = VaultService(db)
    await svc.delete_vault(vault_id, current_user.tenant_id)
    await db.commit()
    return success(None)


# ── 出入库 ────────────────────────────────────────────────────────────────────


@router.get("/inout", response_model=ResponseModel[dict])
async def list_inout(
    direction: Optional[str] = Query(None),
    biz_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    keyword: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = InoutService(db)
    total, records = await svc.list_records(
        current_user.tenant_id,
        direction=direction,
        biz_type=biz_type,
        status=status,
        keyword=keyword,
        skip=skip,
        limit=limit,
    )
    items = [InoutOut.model_validate(r).model_dump(mode="json") for r in records]
    return success({"total": total, "items": items})


@router.post("/inout", response_model=ResponseModel[InoutOut])
async def create_inout(
    body: InoutCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = InoutService(db)
    record = await svc.create_record(body, current_user.id, current_user.tenant_id)
    await db.commit()
    return success(InoutOut.model_validate(record).model_dump(mode="json"))


@router.post("/inout/{record_id}/return", response_model=ResponseModel[InoutOut])
async def return_inout(
    record_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = InoutService(db)
    record = await svc.mark_returned(record_id, current_user.id, current_user.tenant_id)
    await db.commit()
    return success(InoutOut.model_validate(record).model_dump(mode="json"))


# ── 保管台账 ──────────────────────────────────────────────────────────────────


@router.get("/ledger", response_model=ResponseModel[dict])
async def storage_ledger(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = VaultService(db)
    return success(await svc.ledger(current_user.tenant_id))
