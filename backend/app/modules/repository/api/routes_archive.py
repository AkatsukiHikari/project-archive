import uuid
from typing import Optional

from fastapi import APIRouter, Body, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.response import ResponseModel, success
from app.infra.db.session import get_db
from app.modules.iam.api.dependencies import get_current_user
from app.modules.iam.models.user import User
from app.modules.repository.schemas.archive import (
    ArchiveCreate, ArchiveListQuery, ArchiveRead, ArchiveUpdate,
    CatalogCreate, CatalogRead,
)
from app.modules.repository.services.archive_service import ArchiveService, CatalogService
from app.modules.repository.services.es_sync_service import delete_one, sync_one

router = APIRouter(tags=["档案管理"])


# ── 目录 ──────────────────────────────────────────────────────────────────────

@router.get("/archive/catalogs", response_model=ResponseModel[list[CatalogRead]])
async def list_catalogs(
    fonds_id: uuid.UUID = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = CatalogService(db)
    items = await svc.list_by_fonds(fonds_id)
    return success([CatalogRead.model_validate(i) for i in items])


@router.post("/archive/catalogs", response_model=ResponseModel[CatalogRead])
async def create_catalog(
    data: CatalogCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = CatalogService(db)
    item = await svc.create(data, tenant_id=current_user.tenant_id)
    await db.commit()
    return success(CatalogRead.model_validate(item))


@router.delete("/archive/catalogs/{catalog_id}", response_model=ResponseModel[None])
async def delete_catalog(
    catalog_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = CatalogService(db)
    await svc.delete(catalog_id)
    await db.commit()
    return success()


# ── 档案 ──────────────────────────────────────────────────────────────────────

@router.get("/archive/records", response_model=ResponseModel[dict])
async def list_archives(
    fonds_id: Optional[uuid.UUID] = Query(default=None),
    catalog_id: Optional[uuid.UUID] = Query(default=None),
    category_id: Optional[uuid.UUID] = Query(default=None),
    year: Optional[int] = Query(default=None),
    keyword: Optional[str] = Query(default=None),
    security_level: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = ArchiveListQuery(
        fonds_id=fonds_id, catalog_id=catalog_id, category_id=category_id,
        year=year, keyword=keyword, security_level=security_level,
        status=status, page=page, page_size=page_size,
    )
    svc = ArchiveService(db)
    items, total = await svc.list_archives(query, tenant_id=current_user.tenant_id)
    return success({
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [ArchiveRead.model_validate(i) for i in items],
    })


@router.post("/archive/records", response_model=ResponseModel[ArchiveRead])
async def create_archive(
    data: ArchiveCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = ArchiveService(db)
    item = await svc.create(data, tenant_id=current_user.tenant_id)
    await db.commit()
    await sync_one(item)   # PG 提交后异步同步 ES（失败只记日志）
    return success(ArchiveRead.model_validate(item))


@router.get("/archive/records/{archive_id}", response_model=ResponseModel[ArchiveRead])
async def get_archive(
    archive_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = ArchiveService(db)
    item = await svc.get(archive_id)
    return success(ArchiveRead.model_validate(item))


@router.put("/archive/records/{archive_id}", response_model=ResponseModel[ArchiveRead])
async def update_archive(
    archive_id: uuid.UUID,
    data: ArchiveUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = ArchiveService(db)
    item = await svc.update(archive_id, data)
    await db.commit()
    await sync_one(item)   # 更新后同步 ES
    return success(ArchiveRead.model_validate(item))


@router.delete("/archive/records/{archive_id}", response_model=ResponseModel[None])
async def delete_archive(
    archive_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = ArchiveService(db)
    await svc.delete(archive_id)
    await db.commit()
    await delete_one(str(archive_id))  # 软删除后从 ES 移除
    return success()


@router.patch("/archive/records/{archive_id}/override-no", response_model=ResponseModel[ArchiveRead])
async def override_archive_no(
    archive_id: uuid.UUID,
    archive_no: str = Body(..., embed=True),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """手动覆盖档号"""
    svc = ArchiveService(db)
    item = await svc.update(archive_id, ArchiveUpdate(archive_no=archive_no))
    await db.commit()
    await sync_one(item)
    return success(ArchiveRead.model_validate(item))


# ── ES 全量重建（管理员） ─────────────────────────────────────────────────────

@router.post("/archive/admin/rebuild-es-index", response_model=ResponseModel[dict])
async def rebuild_es_index(
    current_user: User = Depends(get_current_user),
):
    """触发 ES 全量重建任务（超级管理员）。"""
    from app.modules.repository.tasks.es_rebuild import rebuild_archive_index
    task = rebuild_archive_index.delay(
        str(current_user.tenant_id) if current_user.tenant_id else None
    )
    return success({"task_id": task.id})
