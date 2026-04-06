"""
利用服务 — 档案检索 API
"""

from typing import Any, Optional
from fastapi import APIRouter, Depends, Query

from app.common.response import ResponseModel, success
from app.modules.iam.api.dependencies import get_current_user
from app.modules.iam.models.user import User
from app.infra.search.archive_index import search_items

router = APIRouter()


@router.get(
    "/search",
    summary="档案全文检索",
    description="""
    基于 Elasticsearch 的档案全文检索。

    - 支持多字段检索（题名、责任者）
    - 支持模糊匹配（容错拼写）
    - 返回高亮片段（检索词在标题中的位置）
    - 默认只返回公开档案；管理员可指定密级
    """,
)
async def search_archives(
    q: str = Query(..., min_length=1, max_length=200, description="检索关键词"),
    year: Optional[int] = Query(None, description="年度过滤"),
    fonds_code: Optional[str] = Query(None, description="全宗号过滤"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
) -> dict:
    tenant_id = str(current_user.tenant_id) if current_user.tenant_id else None
    result = await search_items(
        query=q,
        tenant_id=tenant_id,
        year=year,
        fonds_code=fonds_code,
        skip=skip,
        limit=limit,
    )
    return success(data=result)
