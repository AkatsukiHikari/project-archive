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
    CatalogCreate, CatalogRead, CatalogUpdate,
)
from app.modules.repository.services.archive_service import ArchiveService, CatalogService
from app.modules.repository.services.es_sync_service import delete_one, sync_one

router = APIRouter(tags=["档案管理"])


async def _find_archive(db: AsyncSession, raw: str):
    """按 UUID 或 档号(DH) 定位档案；先查暂存库再查正式库。

    AI 链接 / 外部跳转可能传 UUID，也可能传人类可读的档号(如 Q001-HJ-2024-C-00001)，
    两者都要能打开原文，否则路径用 uuid.UUID 强类型会直接 422。
    """
    from sqlalchemy import select
    from app.modules.repository.models.archive import Archive, ArchiveStaging

    try:
        aid = uuid.UUID(raw)
    except (ValueError, AttributeError, TypeError):
        aid = None

    if aid is not None:
        r = await db.execute(
            select(ArchiveStaging).where(
                ArchiveStaging.id == aid, ArchiveStaging.is_deleted == False  # noqa: E712
            )
        )
        obj = r.scalar_one_or_none()
        if obj:
            return obj
        r = await db.execute(select(Archive).where(Archive.id == aid))
        return r.scalars().first()

    # 按档号匹配
    r = await db.execute(
        select(ArchiveStaging)
        .where(ArchiveStaging.DH == raw, ArchiveStaging.is_deleted == False)  # noqa: E712
        .limit(1)
    )
    obj = r.scalar_one_or_none()
    if obj:
        return obj
    r = await db.execute(select(Archive).where(Archive.DH == raw).limit(1))
    return r.scalars().first()


# ── 目录 ──────────────────────────────────────────────────────────────────────

@router.get("/archive/catalogs", response_model=ResponseModel[list[CatalogRead]])
async def list_catalogs(
    fonds_id: uuid.UUID = Query(...),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
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


@router.put("/archive/catalogs/{catalog_id}", response_model=ResponseModel[CatalogRead])
async def update_catalog(
    catalog_id: uuid.UUID,
    data: CatalogUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = CatalogService(db)
    item = await svc.update(catalog_id, data)
    await db.commit()
    return success(CatalogRead.model_validate(item))


@router.delete("/archive/catalogs/{catalog_id}", response_model=ResponseModel[None])
async def delete_catalog(
    catalog_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
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
    ND: Optional[int] = Query(default=None),
    keyword: Optional[str] = Query(default=None),
    MJ: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
    TM: Optional[str] = Query(default=None),
    RZZ: Optional[str] = Query(default=None),
    DH: Optional[str] = Query(default=None),
    BGQX: Optional[str] = Query(default=None),
    ND_from: Optional[int] = Query(default=None),
    ND_to: Optional[int] = Query(default=None),
    WJRQ_from: Optional[str] = Query(default=None),
    WJRQ_to: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = ArchiveListQuery(
        fonds_id=fonds_id, catalog_id=catalog_id, category_id=category_id,
        ND=ND, keyword=keyword, MJ=MJ, status=status,
        TM=TM, RZZ=RZZ, DH=DH, BGQX=BGQX,
        ND_from=ND_from, ND_to=ND_to, WJRQ_from=WJRQ_from, WJRQ_to=WJRQ_to,
        page=page, page_size=page_size,
    )
    svc = ArchiveService(db)
    items, total = await svc.list_archives(query, tenant_id=current_user.tenant_id)

    # 原文附件数（整理页"原文"列）
    from sqlalchemy import func, select
    from app.modules.repository.models.archive import ArchiveAttachment

    counts: dict = {}
    ids = [i.id for i in items]
    if ids:
        rows = await db.execute(
            select(ArchiveAttachment.archive_id, func.count())
            .where(
                ArchiveAttachment.archive_id.in_(ids),
                ArchiveAttachment.is_deleted == False,  # noqa: E712
            )
            .group_by(ArchiveAttachment.archive_id)
        )
        counts = {r[0]: r[1] for r in rows.all()}

    out = []
    for i in items:
        d = ArchiveRead.model_validate(i).model_dump(mode="json")
        d["attachment_count"] = counts.get(i.id, 0)
        out.append(d)
    return success({
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": out,
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
    archive_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    from app.common.error_code import ErrorCode
    from app.common.exceptions.base import NotFoundException

    item = await _find_archive(db, archive_id)
    if item is None:
        raise NotFoundException(code=ErrorCode.ARCHIVE_NOT_FOUND, message="档案不存在")
    return success(ArchiveRead.model_validate(item))


@router.get("/archive/records/{archive_id}/attachments", response_model=ResponseModel[list[dict]])
async def list_archive_attachments(
    archive_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """档案原文附件列表（含预签名直读 URL，供阅览页 PDF 渲染）。

    archive_id 接受 UUID 或 档号(DH)。主附件优先、按 sort_order 排序；
    URL 失败的条目 url=None 不阻断其余。
    """
    from sqlalchemy import select
    from app.infra.storage.factory import storage
    from app.modules.repository.models.archive import ArchiveAttachment
    from app.modules.repository.schemas.archive import AttachmentRead

    found = await _find_archive(db, archive_id)
    if found is None:
        return success([])
    resolved_id = found.id

    result = await db.execute(
        select(ArchiveAttachment)
        .where(
            ArchiveAttachment.archive_id == resolved_id,
            ArchiveAttachment.is_deleted == False,  # noqa: E712
        )
        .order_by(ArchiveAttachment.is_primary.desc(), ArchiveAttachment.sort_order)
    )
    rows = result.scalars().all()
    out: list[dict] = []
    for a in rows:
        try:
            url = storage.get_presigned_url(a.storage_key, a.storage_bucket, expires_seconds=3600)
        except Exception:
            url = None
        item = AttachmentRead.model_validate(a).model_dump(mode="json")
        item["url"] = url
        out.append(item)
    return success(out)


@router.put("/archive/records/{archive_id}", response_model=ResponseModel[ArchiveRead])
async def update_archive(
    archive_id: uuid.UUID,
    data: ArchiveUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
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
    _: User = Depends(get_current_user),
):
    svc = ArchiveService(db)
    await svc.delete(archive_id)
    await db.commit()
    await delete_one(str(archive_id))  # 软删除后从 ES 移除
    return success()


@router.patch("/archive/records/{archive_id}/override-no", response_model=ResponseModel[ArchiveRead])
async def override_archive_no(
    archive_id: uuid.UUID,
    DH: str = Body(..., embed=True),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """手动覆盖档号"""
    svc = ArchiveService(db)
    item = await svc.update(archive_id, ArchiveUpdate(DH=DH))
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
