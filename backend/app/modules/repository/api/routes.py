"""
档案库 REST API 路由

端点设计（REST 层级关系）：
  全宗：   GET/POST  /repository/fonds
           GET/PUT/DELETE /repository/fonds/{id}
  案卷：   GET/POST  /repository/fonds/{fonds_id}/files
           GET/PUT/DELETE /repository/files/{file_id}
  文件条目：GET/POST  /repository/files/{file_id}/items
            GET/PUT/DELETE /repository/items/{item_id}
"""

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.response import ResponseModel, success
from app.infra.db.session import get_db
from app.modules.iam.models.user import User
from app.modules.iam.api.dependencies import get_current_user
from app.core.security.permissions import require_permissions
from app.modules.repository.schemas.archive import (
    FondsCreate, FondsUpdate, FondsOut,
    ArchiveFileCreate, ArchiveFileUpdate, ArchiveFileOut,
    ArchiveItemCreate, ArchiveItemUpdate, ArchiveItemOut,
)
from app.modules.repository.repositories.archive_repository import (
    FondsRepository, ArchiveFileRepository, ArchiveItemRepository,
)
from app.modules.repository.services.archive_service import (
    FondsService, ArchiveFileService, ArchiveItemService,
)

router = APIRouter()


# ── DI 工厂 ──────────────────────────────────────────────────────────────────

def get_fonds_service(db: AsyncSession = Depends(get_db)) -> FondsService:
    return FondsService(FondsRepository(db))

def get_file_service(db: AsyncSession = Depends(get_db)) -> ArchiveFileService:
    return ArchiveFileService(ArchiveFileRepository(db), FondsRepository(db))

def get_item_service(db: AsyncSession = Depends(get_db)) -> ArchiveItemService:
    return ArchiveItemService(ArchiveItemRepository(db), ArchiveFileRepository(db))


# ── 全宗 CRUD ─────────────────────────────────────────────────────────────────

@router.get(
    "/fonds",
    response_model=ResponseModel[List[FondsOut]],
    summary="获取全宗列表",
)
async def list_fonds(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    service: FondsService = Depends(get_fonds_service),
) -> dict:
    fonds_list = await service.list_fonds(current_user, skip=skip, limit=limit)
    return success(data=[FondsOut.model_validate(f).model_dump(mode="json") for f in fonds_list])


@router.post(
    "/fonds",
    response_model=ResponseModel[FondsOut],
    summary="创建全宗",
)
async def create_fonds(
    body: FondsCreate,
    current_user: User = Depends(require_permissions("repository:fonds:create")),
    service: FondsService = Depends(get_fonds_service),
) -> dict:
    fonds = await service.create_fonds(body, current_user)
    return success(data=FondsOut.model_validate(fonds).model_dump(mode="json"))


@router.get(
    "/fonds/{fonds_id}",
    response_model=ResponseModel[FondsOut],
    summary="获取全宗详情",
)
async def get_fonds(
    fonds_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: FondsService = Depends(get_fonds_service),
) -> dict:
    fonds = await service.get_fonds(fonds_id)
    return success(data=FondsOut.model_validate(fonds).model_dump(mode="json"))


@router.put(
    "/fonds/{fonds_id}",
    response_model=ResponseModel[FondsOut],
    summary="更新全宗",
)
async def update_fonds(
    fonds_id: uuid.UUID,
    body: FondsUpdate,
    current_user: User = Depends(require_permissions("repository:fonds:update")),
    service: FondsService = Depends(get_fonds_service),
) -> dict:
    fonds = await service.update_fonds(fonds_id, body)
    return success(data=FondsOut.model_validate(fonds).model_dump(mode="json"))


@router.delete(
    "/fonds/{fonds_id}",
    response_model=ResponseModel,
    summary="删除全宗（软删除）",
)
async def delete_fonds(
    fonds_id: uuid.UUID,
    current_user: User = Depends(require_permissions("repository:fonds:delete")),
    service: FondsService = Depends(get_fonds_service),
) -> dict:
    await service.delete_fonds(fonds_id)
    return success(message="全宗已删除")


# ── 案卷 CRUD ─────────────────────────────────────────────────────────────────

@router.get(
    "/fonds/{fonds_id}/files",
    response_model=ResponseModel[List[ArchiveFileOut]],
    summary="获取全宗下的案卷列表",
)
async def list_archive_files(
    fonds_id: uuid.UUID,
    year: Optional[int] = Query(None, description="按年度筛选"),
    security_level: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    service: ArchiveFileService = Depends(get_file_service),
) -> dict:
    files = await service.list_by_fonds(
        fonds_id, year=year, security_level=security_level,
        skip=skip, limit=limit,
    )
    return success(data=[ArchiveFileOut.model_validate(f).model_dump(mode="json") for f in files])


@router.post(
    "/files",
    response_model=ResponseModel[ArchiveFileOut],
    summary="创建案卷",
)
async def create_archive_file(
    body: ArchiveFileCreate,
    current_user: User = Depends(require_permissions("repository:file:create")),
    service: ArchiveFileService = Depends(get_file_service),
) -> dict:
    af = await service.create_archive_file(body, current_user)
    return success(data=ArchiveFileOut.model_validate(af).model_dump(mode="json"))


@router.get(
    "/files/{file_id}",
    response_model=ResponseModel[ArchiveFileOut],
    summary="获取案卷详情",
)
async def get_archive_file(
    file_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: ArchiveFileService = Depends(get_file_service),
) -> dict:
    af = await service.get_archive_file(file_id)
    return success(data=ArchiveFileOut.model_validate(af).model_dump(mode="json"))


@router.put(
    "/files/{file_id}",
    response_model=ResponseModel[ArchiveFileOut],
    summary="更新案卷",
)
async def update_archive_file(
    file_id: uuid.UUID,
    body: ArchiveFileUpdate,
    current_user: User = Depends(require_permissions("repository:file:update")),
    service: ArchiveFileService = Depends(get_file_service),
) -> dict:
    af = await service.update_archive_file(file_id, body)
    return success(data=ArchiveFileOut.model_validate(af).model_dump(mode="json"))


@router.delete(
    "/files/{file_id}",
    response_model=ResponseModel,
    summary="删除案卷（软删除）",
)
async def delete_archive_file(
    file_id: uuid.UUID,
    current_user: User = Depends(require_permissions("repository:file:delete")),
    service: ArchiveFileService = Depends(get_file_service),
) -> dict:
    await service.delete_archive_file(file_id)
    return success(message="案卷已删除")


# ── 文件条目 CRUD ──────────────────────────────────────────────────────────────

@router.get(
    "/files/{file_id}/items",
    response_model=ResponseModel[List[ArchiveItemOut]],
    summary="获取案卷下的文件条目列表",
)
async def list_archive_items(
    file_id: uuid.UUID,
    item_type: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    service: ArchiveItemService = Depends(get_item_service),
) -> dict:
    items = await service.list_by_archive_file(
        file_id, item_type=item_type, skip=skip, limit=limit
    )
    return success(data=[ArchiveItemOut.model_validate(i).model_dump(mode="json") for i in items])


@router.post(
    "/items",
    response_model=ResponseModel[ArchiveItemOut],
    summary="创建文件条目",
)
async def create_archive_item(
    body: ArchiveItemCreate,
    current_user: User = Depends(require_permissions("repository:item:create")),
    service: ArchiveItemService = Depends(get_item_service),
) -> dict:
    item = await service.create_item(body, current_user)
    return success(data=ArchiveItemOut.model_validate(item).model_dump(mode="json"))


@router.get(
    "/items/{item_id}",
    response_model=ResponseModel[ArchiveItemOut],
    summary="获取文件条目详情",
)
async def get_archive_item(
    item_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: ArchiveItemService = Depends(get_item_service),
) -> dict:
    item = await service.get_item(item_id)
    return success(data=ArchiveItemOut.model_validate(item).model_dump(mode="json"))


@router.put(
    "/items/{item_id}",
    response_model=ResponseModel[ArchiveItemOut],
    summary="更新文件条目",
)
async def update_archive_item(
    item_id: uuid.UUID,
    body: ArchiveItemUpdate,
    current_user: User = Depends(require_permissions("repository:item:update")),
    service: ArchiveItemService = Depends(get_item_service),
) -> dict:
    item = await service.update_item(item_id, body)
    return success(data=ArchiveItemOut.model_validate(item).model_dump(mode="json"))


@router.delete(
    "/items/{item_id}",
    response_model=ResponseModel,
    summary="删除文件条目（软删除）",
)
async def delete_archive_item(
    item_id: uuid.UUID,
    current_user: User = Depends(require_permissions("repository:item:delete")),
    service: ArchiveItemService = Depends(get_item_service),
) -> dict:
    await service.delete_item(item_id)
    return success(message="文件条目已删除")
