"""鉴定标准条款 / 敏感词库 维护 API。

挂载前缀： /appraisal
  标准条款  GET/POST /standards, PUT/DELETE /standards/{id}
  敏感词    GET/POST /words, PUT/DELETE /words/{id}
"""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.response import ResponseModel, success
from app.core.security.permissions import require_permissions
from app.infra.db.session import get_db
from app.modules.appraisal.schemas.standard import (SensitiveWordCreate,
                                                    SensitiveWordOut,
                                                    SensitiveWordUpdate,
                                                    StandardCreate,
                                                    StandardOut,
                                                    StandardUpdate)
from app.modules.appraisal.services.standard_service import StandardService
from app.modules.iam.api.dependencies import get_current_user
from app.modules.iam.models.user import User

router = APIRouter(prefix="/appraisal", tags=["鉴定标准"])


# ── 标准条款 ──────────────────────────────────────────────────────────────────


@router.get("/standards", response_model=ResponseModel[list[StandardOut]])
async def list_standards(
    enabled_only: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = StandardService(db)
    standards = await svc.list_standards(current_user.tenant_id, enabled_only)
    return success(
        [StandardOut.model_validate(s).model_dump(mode="json") for s in standards]
    )


@router.post("/standards", response_model=ResponseModel[StandardOut])
async def create_standard(
    body: StandardCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("appraisal:standard")),
):
    svc = StandardService(db)
    standard = await svc.create_standard(body, current_user.id, current_user.tenant_id)
    await db.commit()
    return success(StandardOut.model_validate(standard).model_dump(mode="json"))


@router.put("/standards/{standard_id}", response_model=ResponseModel[StandardOut])
async def update_standard(
    standard_id: uuid.UUID,
    body: StandardUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("appraisal:standard")),
):
    svc = StandardService(db)
    standard = await svc.update_standard(standard_id, body, current_user.tenant_id)
    await db.commit()
    return success(StandardOut.model_validate(standard).model_dump(mode="json"))


@router.delete("/standards/{standard_id}", response_model=ResponseModel[None])
async def delete_standard(
    standard_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("appraisal:standard")),
):
    svc = StandardService(db)
    await svc.delete_standard(standard_id, current_user.tenant_id)
    await db.commit()
    return success(None)


# ── 敏感词 ────────────────────────────────────────────────────────────────────


@router.get("/words", response_model=ResponseModel[dict])
async def list_words(
    keyword: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = StandardService(db)
    total, words = await svc.list_words(
        current_user.tenant_id, keyword=keyword, skip=skip, limit=limit
    )
    return success(
        {
            "total": total,
            "items": [
                SensitiveWordOut.model_validate(w).model_dump(mode="json")
                for w in words
            ],
        }
    )


@router.post("/words", response_model=ResponseModel[SensitiveWordOut])
async def create_word(
    body: SensitiveWordCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("appraisal:standard")),
):
    svc = StandardService(db)
    word = await svc.create_word(body, current_user.id, current_user.tenant_id)
    await db.commit()
    return success(SensitiveWordOut.model_validate(word).model_dump(mode="json"))


@router.put("/words/{word_id}", response_model=ResponseModel[SensitiveWordOut])
async def update_word(
    word_id: uuid.UUID,
    body: SensitiveWordUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("appraisal:standard")),
):
    svc = StandardService(db)
    word = await svc.update_word(word_id, body, current_user.tenant_id)
    await db.commit()
    return success(SensitiveWordOut.model_validate(word).model_dump(mode="json"))


@router.delete("/words/{word_id}", response_model=ResponseModel[None])
async def delete_word(
    word_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("appraisal:standard")),
):
    svc = StandardService(db)
    await svc.delete_word(word_id, current_user.tenant_id)
    await db.commit()
    return success(None)
