"""档案编研 API。挂载前缀 /research。

项目  GET/POST /projects, GET/PUT/DELETE /projects/{id}
选材  GET/POST /projects/{id}/materials, DELETE /materials/{material_id}
成果  GET/POST /results, GET/PUT/DELETE /results/{id},
      POST /results/{id}/{submit|finalize|publish|reopen}
成果档案库  GET/POST /results/{id}/archives, DELETE /result-archives/{ra_id}
编纂辅助  POST /results/{id}/chronicle-table（按档案库生成大事记表格 HTML）
          POST /ai-draft（AI 依据成果档案库生成可插入 HTML）
模板  GET/POST /templates, GET/PUT/DELETE /templates/{id}
上传  POST /upload（编辑器图片/附件）
"""

import io
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, File, Path, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.response import ResponseModel, success
from app.infra.db.session import get_db
from app.infra.storage.factory import storage
from app.modules.iam.api.dependencies import get_current_user
from app.modules.iam.models.user import User
from app.modules.research.schemas.research import (
    AiDraftRequest,
    AiDraftResult,
    MaterialAdd,
    MaterialOut,
    ProjectCreate,
    ProjectOut,
    ProjectUpdate,
    ResultArchiveAdd,
    ResultArchiveOut,
    ResultCreate,
    ResultListItem,
    ResultOut,
    ResultUpdate,
    TemplateCreate,
    TemplateOut,
    TemplateUpdate,
    UploadResult,
)
from app.modules.research.services.ai_draft_service import AiDraftService
from app.modules.research.services.project_service import ProjectService
from app.modules.research.services.result_service import ResultService
from app.modules.research.services.template_service import TemplateService

router = APIRouter(prefix="/research", tags=["档案编研"])

RESEARCH_BUCKET = "research"


# ── 项目 ──────────────────────────────────────────────────────────────────────


@router.get("/projects", response_model=ResponseModel[list[ProjectOut]])
async def list_projects(
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = ProjectService(db)
    data = await svc.list_projects(current_user.tenant_id, status=status)
    return success([ProjectOut.model_validate(p).model_dump(mode="json") for p in data])


@router.post("/projects", response_model=ResponseModel[ProjectOut])
async def create_project(
    body: ProjectCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = ProjectService(db)
    p = await svc.create_project(body, current_user.id, current_user.tenant_id)
    await db.commit()
    data = await svc.get_project(p.id, current_user.tenant_id)
    return success(ProjectOut.model_validate(data).model_dump(mode="json"))


@router.get("/projects/{project_id}", response_model=ResponseModel[ProjectOut])
async def get_project(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = ProjectService(db)
    data = await svc.get_project(project_id, current_user.tenant_id)
    return success(ProjectOut.model_validate(data).model_dump(mode="json"))


@router.put("/projects/{project_id}", response_model=ResponseModel[ProjectOut])
async def update_project(
    project_id: uuid.UUID,
    body: ProjectUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = ProjectService(db)
    await svc.update_project(project_id, body, current_user.tenant_id)
    await db.commit()
    data = await svc.get_project(project_id, current_user.tenant_id)
    return success(ProjectOut.model_validate(data).model_dump(mode="json"))


@router.delete("/projects/{project_id}", response_model=ResponseModel[None])
async def delete_project(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = ProjectService(db)
    await svc.delete_project(project_id, current_user.tenant_id)
    await db.commit()
    return success(None)


# ── 选材 ──────────────────────────────────────────────────────────────────────


@router.get(
    "/projects/{project_id}/materials", response_model=ResponseModel[list[MaterialOut]]
)
async def list_materials(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = ProjectService(db)
    mats = await svc.list_materials(project_id, current_user.tenant_id)
    return success(
        [MaterialOut.model_validate(m).model_dump(mode="json") for m in mats]
    )


@router.post("/projects/{project_id}/materials", response_model=ResponseModel[dict])
async def add_materials(
    project_id: uuid.UUID,
    body: MaterialAdd,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = ProjectService(db)
    added = await svc.add_materials(
        project_id, body.archive_ids, current_user.tenant_id
    )
    await db.commit()
    return success({"added": added})


@router.delete("/materials/{material_id}", response_model=ResponseModel[None])
async def remove_material(
    material_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = ProjectService(db)
    await svc.remove_material(material_id, current_user.tenant_id)
    await db.commit()
    return success(None)


# ── 成果 ──────────────────────────────────────────────────────────────────────


@router.get("/results", response_model=ResponseModel[dict])
async def list_results(
    result_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    project_id: Optional[uuid.UUID] = Query(None),
    keyword: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = ResultService(db)
    total, items = await svc.list_results(
        current_user.tenant_id,
        result_type=result_type,
        status=status,
        project_id=project_id,
        keyword=keyword,
        skip=skip,
        limit=limit,
    )
    return success(
        {
            "total": total,
            "items": [
                ResultListItem.model_validate(i).model_dump(mode="json") for i in items
            ],
        }
    )


@router.post("/results", response_model=ResponseModel[ResultOut])
async def create_result(
    body: ResultCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = ResultService(db)
    r = await svc.create_result(body, current_user.id, current_user.tenant_id)
    await db.commit()
    return success(
        ResultOut.model_validate(
            await svc.get_result(r.id, current_user.tenant_id)
        ).model_dump(mode="json")
    )


@router.get("/results/{result_id}", response_model=ResponseModel[ResultOut])
async def get_result(
    result_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = ResultService(db)
    return success(
        ResultOut.model_validate(
            await svc.get_result(result_id, current_user.tenant_id)
        ).model_dump(mode="json")
    )


@router.put("/results/{result_id}", response_model=ResponseModel[ResultOut])
async def update_result(
    result_id: uuid.UUID,
    body: ResultUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = ResultService(db)
    await svc.update_result(result_id, body, current_user.tenant_id)
    await db.commit()
    return success(
        ResultOut.model_validate(
            await svc.get_result(result_id, current_user.tenant_id)
        ).model_dump(mode="json")
    )


@router.delete("/results/{result_id}", response_model=ResponseModel[None])
async def delete_result(
    result_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = ResultService(db)
    await svc.delete_result(result_id, current_user.tenant_id)
    await db.commit()
    return success(None)


# ── 成果档案库 ────────────────────────────────────────────────────────────────


@router.get(
    "/results/{result_id}/archives",
    response_model=ResponseModel[list[ResultArchiveOut]],
)
async def list_result_archives(
    result_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = ResultService(db)
    rows = await svc.list_archives(result_id, current_user.tenant_id)
    return success(
        [ResultArchiveOut.model_validate(x).model_dump(mode="json") for x in rows]
    )


@router.post("/results/{result_id}/archives", response_model=ResponseModel[dict])
async def add_result_archives(
    result_id: uuid.UUID,
    body: ResultArchiveAdd,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = ResultService(db)
    added = await svc.add_archives(
        result_id, body.archive_ids, body.from_project, current_user.tenant_id
    )
    await db.commit()
    return success({"added": added})


@router.delete("/result-archives/{ra_id}", response_model=ResponseModel[None])
async def remove_result_archive(
    ra_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = ResultService(db)
    await svc.remove_archive(ra_id, current_user.tenant_id)
    await db.commit()
    return success(None)


# ── 编纂辅助 ──────────────────────────────────────────────────────────────────


@router.post("/results/{result_id}/chronicle-table", response_model=ResponseModel[dict])
async def chronicle_table(
    result_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """按成果档案库的文件日期排序，生成大事记表格 HTML（不走 AI）。"""
    svc = ResultService(db)
    html_str = await svc.chronicle_html(result_id, current_user.tenant_id)
    return success({"html": html_str})


@router.post("/ai-draft", response_model=ResponseModel[AiDraftResult])
async def ai_draft(
    body: AiDraftRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """AI 依据成果档案库生成可插入文档的 HTML 草稿（大事记表格 / 提要+正文）。"""
    svc = AiDraftService(db)
    data = await svc.draft(
        body.result_id, body.topic, current_user.id, current_user.tenant_id
    )
    return success(AiDraftResult.model_validate(data).model_dump(mode="json"))


# ── 模板 ──────────────────────────────────────────────────────────────────────


@router.get("/templates", response_model=ResponseModel[list[TemplateOut]])
async def list_templates(
    result_type: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = TemplateService(db)
    rows = await svc.list_templates(current_user.tenant_id, result_type=result_type)
    return success(
        [TemplateOut.model_validate(t).model_dump(mode="json") for t in rows]
    )


@router.post("/templates", response_model=ResponseModel[TemplateOut])
async def create_template(
    body: TemplateCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = TemplateService(db)
    t = await svc.create_template(body, current_user.id, current_user.tenant_id)
    await db.commit()
    return success(TemplateOut.model_validate(t).model_dump(mode="json"))


@router.get("/templates/{template_id}", response_model=ResponseModel[TemplateOut])
async def get_template(
    template_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = TemplateService(db)
    t = await svc.get_template(template_id, current_user.tenant_id)
    return success(TemplateOut.model_validate(t).model_dump(mode="json"))


@router.put("/templates/{template_id}", response_model=ResponseModel[TemplateOut])
async def update_template(
    template_id: uuid.UUID,
    body: TemplateUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = TemplateService(db)
    t = await svc.update_template(template_id, body, current_user.tenant_id)
    await db.commit()
    return success(TemplateOut.model_validate(t).model_dump(mode="json"))


@router.delete("/templates/{template_id}", response_model=ResponseModel[None])
async def delete_template(
    template_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = TemplateService(db)
    await svc.delete_template(template_id, current_user.tenant_id)
    await db.commit()
    return success(None)


# ── 上传（编辑器图片/附件）────────────────────────────────────────────────────


@router.post("/upload", response_model=ResponseModel[UploadResult])
async def upload_asset(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    content = await file.read()
    ext = (file.filename or "").rsplit(".", 1)[-1].lower() if file.filename else "bin"
    key = f"{uuid.uuid4().hex}.{ext}"
    storage.save(
        io.BytesIO(content),
        key,
        RESEARCH_BUCKET,
        file.content_type or "application/octet-stream",
    )
    url = storage.get_presigned_url(key, RESEARCH_BUCKET)
    return success(
        UploadResult(
            id=key,
            url=url,
            name=file.filename or key,
            size=len(content),
            type=file.content_type or "application/octet-stream",
        ).model_dump(mode="json")
    )


# ── 成果状态流转（catch-all，必须最后注册，避免吃掉上面的 /results/{id}/xxx）──────


@router.post("/results/{result_id}/{action}", response_model=ResponseModel[ResultOut])
async def transition_result(
    result_id: uuid.UUID,
    action: str = Path(pattern="^(submit|finalize|publish|reopen)$"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """成果状态流转：submit 提交审核 / finalize 定稿 / publish 发布 / reopen 撤回。"""
    svc = ResultService(db)
    await svc.transition(result_id, action, current_user.id, current_user.tenant_id)
    await db.commit()
    return success(
        ResultOut.model_validate(
            await svc.get_result(result_id, current_user.tenant_id)
        ).model_dump(mode="json")
    )
