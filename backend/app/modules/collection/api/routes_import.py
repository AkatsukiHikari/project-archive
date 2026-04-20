"""
批量导入 API 路由。

POST  /archive/import/upload         上传文件 → 返回 task_id + 列头
POST  /archive/import/mapping        保存字段映射快照
POST  /archive/import/dry-run        预检（不写库）
POST  /archive/import/execute        触发 Celery 异步导入
GET   /archive/import/tasks          查询当前租户的导入任务列表
GET   /archive/import/tasks/{id}     查询单个任务进度
GET   /archive/import/tasks/{id}/report  下载失败报表（预签名 URL）

GET   /archive/import/mapping-templates           查询映射模板列表
DELETE /archive/import/mapping-templates/{id}     删除模板
"""
import uuid

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.response import ResponseModel, success
from app.infra.db.session import get_db
from app.infra.storage.factory import storage
from app.modules.collection.repositories.import_repo import ImportTaskRepository
from app.modules.collection.schemas.import_schema import (
    DryRunResponse,
    ExecuteRequest,
    ImportTaskRead,
    MappingPreviewRequest,
    MappingTemplateRead,
    UploadResponse,
)
from app.modules.collection.services.import_service import ImportService
from app.modules.collection.services.mapping_service import MappingTemplateRepository
from app.modules.iam.api.dependencies import get_current_user
from app.modules.iam.models.user import User

router = APIRouter(prefix="/archive/import", tags=["批量导入"])


# ── 上传文件 ──────────────────────────────────────────────────────────────────

@router.post("/upload", response_model=ResponseModel[UploadResponse])
async def upload_file(
    file: UploadFile = File(...),
    category_id: uuid.UUID = Form(...),
    fonds_id: uuid.UUID = Form(...),
    catalog_id: uuid.UUID = Form(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    file_bytes = await file.read()
    svc = ImportService(db)
    result = await svc.upload(
        file_bytes=file_bytes,
        filename=file.filename or "upload.csv",
        category_id=category_id,
        fonds_id=fonds_id,
        catalog_id=catalog_id,
        operator_id=current_user.id,
        tenant_id=current_user.tenant_id,
    )
    await db.commit()
    return success(result)


# ── 保存字段映射 ──────────────────────────────────────────────────────────────

@router.post("/mapping", response_model=ResponseModel[None])
async def save_mapping(
    req: MappingPreviewRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = ImportService(db)
    await svc.save_mapping(
        task_id=req.task_id,
        mappings=req.mappings,
        save_as_template=req.save_as_template,
        tenant_id=current_user.tenant_id,
    )
    await db.commit()
    return success()


# ── Dry-run 预检 ──────────────────────────────────────────────────────────────

@router.post("/dry-run", response_model=ResponseModel[DryRunResponse])
async def dry_run(
    req: ExecuteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = ImportService(db)
    report = await svc.dry_run(req.task_id, current_user.tenant_id)
    await db.commit()
    return success(report)


# ── 触发异步导入 ──────────────────────────────────────────────────────────────

@router.post("/execute", response_model=ResponseModel[ImportTaskRead])
async def execute_import(
    req: ExecuteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.modules.collection.tasks.import_task import execute_import as celery_task

    svc = ImportService(db)
    task = await svc.get_task(req.task_id, current_user.tenant_id)
    if task.status not in ("pending", "failed"):
        from app.common.exceptions.base import ValidationException
        raise ValidationException(message=f"任务状态为 {task.status}，无法重新执行")

    # 提交 Celery 任务（非阻塞）
    celery_task.delay(str(task.id))
    return success(ImportTaskRead.model_validate(task))


# ── 任务查询 ──────────────────────────────────────────────────────────────────

@router.get("/tasks", response_model=ResponseModel[list[ImportTaskRead]])
async def list_tasks(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    repo = ImportTaskRepository(db)
    tasks = await repo.list_by_tenant(current_user.tenant_id, skip=skip, limit=limit)
    return success([ImportTaskRead.model_validate(t) for t in tasks])


@router.get("/tasks/{task_id}", response_model=ResponseModel[ImportTaskRead])
async def get_task(
    task_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = ImportService(db)
    task = await svc.get_task(task_id, current_user.tenant_id)
    return success(ImportTaskRead.model_validate(task))


@router.get("/tasks/{task_id}/report")
async def download_report(
    task_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """返回失败报表的预签名下载 URL。"""
    svc = ImportService(db)
    task = await svc.get_task(task_id, current_user.tenant_id)
    if not task.error_report_key:
        from app.common.exceptions.base import NotFoundException
        raise NotFoundException(message="该任务没有失败报表")
    url = storage.get_presigned_url(task.error_report_key, "import-staging", expires=3600)
    return success({"url": url})


# ── 映射模板 ──────────────────────────────────────────────────────────────────

@router.get("/mapping-templates", response_model=ResponseModel[list[MappingTemplateRead]])
async def list_mapping_templates(
    category_id: uuid.UUID = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    repo = MappingTemplateRepository(db)
    templates = await repo.list_by_category(category_id, current_user.tenant_id)
    return success([MappingTemplateRead.model_validate(t) for t in templates])
