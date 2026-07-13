import uuid
from typing import Optional

from fastapi import APIRouter, Body, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.response import ResponseModel, success
from app.infra.db.session import get_db
from app.modules.iam.api.dependencies import get_current_user
from app.modules.iam.models.user import User
from app.modules.repository.schemas.archive import (
    ArchiveCreate,
    ArchiveListQuery,
    ArchiveRead,
    ArchiveUpdate,
    CatalogCreate,
    CatalogRead,
    CatalogUpdate,
)
from app.modules.repository.services.archive_service import (
    ArchiveService,
    CatalogService,
)
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
                ArchiveStaging.id == aid,
                ArchiveStaging.is_deleted == False,  # noqa: E712
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
        .where(
            ArchiveStaging.DH == raw, ArchiveStaging.is_deleted == False
        )  # noqa: E712
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


# ── 目录导航树（门类 → 全宗号 → 年度，逐层懒加载） ─────────────────────────────


@router.get("/archive/records/nav", response_model=ResponseModel[list[dict]])
async def archive_nav_tree(
    level: str = Query(..., pattern="^(category|fonds|year)$"),
    category_id: Optional[uuid.UUID] = Query(default=None),
    fonds_id: Optional[uuid.UUID] = Query(default=None),
    source: str = Query(default="staging", description="staging 暂存库 | formal 正式库 | all 两库合并"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """档案查询的层级导航：门类→全宗号→年度，每级带条目计数，供老档案员点选过滤。

    source 决定口径：著录页=暂存库，档案查询页=正式库，智能校对页=all（两库计数合并）。
    """
    from sqlalchemy import func, select
    from app.modules.repository.models.archive import Archive, ArchiveStaging
    from app.modules.repository.models.category import ArchiveCategory

    if source == "formal":
        models = [Archive]
    elif source == "all":
        models = [ArchiveStaging, Archive]
    else:
        models = [ArchiveStaging]

    tenant_id = current_user.tenant_id

    def _conds(model):
        conds = [model.is_deleted == False]  # noqa: E712
        if tenant_id:
            conds.append(model.tenant_id == tenant_id)
        return conds

    if level == "category":
        merged: dict = {}
        for model in models:
            stmt = (
                select(
                    model.category_id,
                    ArchiveCategory.code,
                    ArchiveCategory.name,
                    func.count(),
                )
                .join(ArchiveCategory, model.category_id == ArchiveCategory.id)
                .where(*_conds(model))
                .group_by(model.category_id, ArchiveCategory.code, ArchiveCategory.name)
            )
            for r in (await db.execute(stmt)).all():
                key = str(r[0])
                if key in merged:
                    merged[key] = {**merged[key], "count": merged[key]["count"] + r[3]}
                else:
                    merged[key] = {"category_id": key, "code": r[1], "name": r[2], "count": r[3]}
        return success(sorted(merged.values(), key=lambda x: x["code"] or ""))

    if level == "fonds":
        if not category_id:
            return success([])
        merged = {}
        for model in models:
            stmt = (
                select(model.QZH, model.fonds_id, func.count())
                .where(*_conds(model), model.category_id == category_id)
                .group_by(model.QZH, model.fonds_id)
            )
            for r in (await db.execute(stmt)).all():
                key = str(r[1])
                if key in merged:
                    merged[key] = {**merged[key], "count": merged[key]["count"] + r[2]}
                else:
                    merged[key] = {"qzh": r[0], "fonds_id": key, "count": r[2]}
        return success(sorted(merged.values(), key=lambda x: x["qzh"] or ""))

    # level == "year"
    if not category_id or not fonds_id:
        return success([])
    merged = {}
    for model in models:
        stmt = (
            select(model.ND, func.count())
            .where(
                *_conds(model),
                model.category_id == category_id,
                model.fonds_id == fonds_id,
            )
            .group_by(model.ND)
        )
        for r in (await db.execute(stmt)).all():
            if r[0] is None:
                continue
            if r[0] in merged:
                merged[r[0]] = {**merged[r[0]], "count": merged[r[0]]["count"] + r[1]}
            else:
                merged[r[0]] = {"year": r[0], "count": r[1]}
    return success(sorted(merged.values(), key=lambda x: x["year"], reverse=True))


# ── 档案 ──────────────────────────────────────────────────────────────────────


@router.get("/archive/records", response_model=ResponseModel[dict])
async def list_archives(
    source: str = Query(default="staging", description="staging 暂存库 | formal 正式库"),
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
        fonds_id=fonds_id,
        catalog_id=catalog_id,
        category_id=category_id,
        ND=ND,
        keyword=keyword,
        MJ=MJ,
        status=status,
        TM=TM,
        RZZ=RZZ,
        DH=DH,
        BGQX=BGQX,
        ND_from=ND_from,
        ND_to=ND_to,
        WJRQ_from=WJRQ_from,
        WJRQ_to=WJRQ_to,
        page=page,
        page_size=page_size,
    )
    svc = ArchiveService(db)
    items, total = await svc.list_archives(
        query, tenant_id=current_user.tenant_id, source=source
    )

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
    return success(
        {
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": out,
        }
    )


@router.post("/archive/records", response_model=ResponseModel[ArchiveRead])
async def create_archive(
    data: ArchiveCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = ArchiveService(db)
    item = await svc.create(data, tenant_id=current_user.tenant_id)
    await db.commit()
    await sync_one(item)  # PG 提交后异步同步 ES（失败只记日志）
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


@router.get(
    "/archive/records/{archive_id}/attachments",
    response_model=ResponseModel[list[dict]],
)
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
            url = storage.get_presigned_url(
                a.storage_key, a.storage_bucket, expires_seconds=3600
            )
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
    await sync_one(item)  # 更新后同步 ES
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


@router.patch(
    "/archive/records/{archive_id}/override-no",
    response_model=ResponseModel[ArchiveRead],
)
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
    sync: bool = Query(
        False,
        description="true=在当前进程内同步重建（暂存库+正式库），false=投递 Celery 异步任务",
    ),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """ES 全量重建。

    sync=True：在 API 进程内同步重建，覆盖暂存库 + 正式库（含 full_text 全文）。
    sync=False：投递 Celery 异步任务（仅暂存库）。
    """
    if not sync:
        from app.modules.repository.tasks.es_rebuild import rebuild_archive_index

        task = rebuild_archive_index.delay(
            str(current_user.tenant_id) if current_user.tenant_id else None
        )
        return success({"task_id": task.id})

    from sqlalchemy import select
    from app.modules.repository.models.archive import Archive, ArchiveStaging
    from app.modules.repository.services.es_sync_service import bulk_sync

    total = 0
    for model in (ArchiveStaging, Archive):
        rows = (
            (
                await db.execute(
                    select(model).where(model.is_deleted == False)  # noqa: E712
                )
            )
            .scalars()
            .all()
        )
        total += await bulk_sync(rows)
    return success({"reindexed": total, "mode": "sync"})
