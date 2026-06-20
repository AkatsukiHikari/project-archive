"""超级查询（NDL 风格）：字段/全文检索 + 分面聚合，全部走 ES。

该路由**不挂在** v1 的全局登录依赖下（直接由 application 挂载），按登录态分级：
  - 已登录：本租户全部档案（含密级）
  - 匿名：仅开放档案（MJ=无），跨租户
"""

import uuid
from typing import Optional

import jwt
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.response import ResponseModel, success
from app.core.config import settings
from app.core.security.token import ALGORITHM
from app.infra.db.session import get_db
from app.infra.search.archive_index import FACET_FIELDS, super_search
from app.modules.iam.models.user import User
from app.modules.repository.models.category import ArchiveCategory

router = APIRouter(tags=["super-search"])


async def get_optional_user(
    request: Request, db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """可选登录：有合法 Bearer 则返回用户，否则 None（不报错）。"""
    auth = request.headers.get("Authorization", "")
    if not auth.lower().startswith("bearer "):
        return None
    token = auth[7:].strip()
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        user = (
            await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
        ).scalar_one_or_none()
        return user if (user and user.is_active) else None
    except Exception:
        return None


async def _category_names(ids: list[str]) -> dict[str, str]:
    if not ids:
        return {}
    from app.infra.db.session import AsyncSessionLocal

    uuids = []
    for i in ids:
        try:
            uuids.append(uuid.UUID(i))
        except (ValueError, TypeError):
            continue
    if not uuids:
        return {}
    async with AsyncSessionLocal() as db:
        rows = (
            await db.execute(
                select(ArchiveCategory.id, ArchiveCategory.name).where(
                    ArchiveCategory.id.in_(uuids)
                )
            )
        ).all()
    return {str(r[0]): r[1] for r in rows}


async def _archives_with_source(ids: list[str]) -> set[str]:
    """返回有数字化原文(未删除附件)的档案 id 集合。"""
    from app.infra.db.session import AsyncSessionLocal
    from app.modules.repository.models.archive import ArchiveAttachment

    uuids = []
    for i in ids:
        try:
            uuids.append(uuid.UUID(i))
        except (ValueError, TypeError):
            continue
    if not uuids:
        return set()
    async with AsyncSessionLocal() as db:
        rows = (
            (
                await db.execute(
                    select(ArchiveAttachment.archive_id)
                    .where(
                        ArchiveAttachment.archive_id.in_(uuids),
                        ArchiveAttachment.is_deleted.is_(False),
                    )
                    .distinct()
                )
            )
            .scalars()
            .all()
        )
    return {str(r) for r in rows}


@router.get("/archive", response_model=ResponseModel[dict])
async def archive_super_search(
    keyword: Optional[str] = Query(None, max_length=200),
    mode: str = Query("field", pattern="^(field|fulltext)$"),
    QZH: list[str] = Query(default=[]),
    ND: list[int] = Query(default=[]),
    RZZ: list[str] = Query(default=[]),
    MJ: list[str] = Query(default=[]),
    BGQX: list[str] = Query(default=[]),
    category_id: list[str] = Query(default=[]),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: Optional[User] = Depends(get_optional_user),
):
    tenant_id = (
        str(current_user.tenant_id)
        if (current_user and current_user.tenant_id)
        else None
    )
    public_only = current_user is None

    filters = {
        "QZH": QZH,
        "ND": ND,
        "RZZ": RZZ,
        "MJ": MJ,
        "BGQX": BGQX,
        "category_id": category_id,
    }
    result = await super_search(
        keyword=keyword or None,
        mode=mode,
        filters=filters,
        tenant_id=tenant_id,
        public_only=public_only,
        skip=(page - 1) * page_size,
        limit=page_size,
    )

    # 标注每条是否有数字化原文（有附件才允许"查看原文"）
    hits = result.get("hits", [])
    have_source = await _archives_with_source([h.get("id") for h in hits])
    for h in hits:
        h["has_source"] = h.get("id") in have_source

    # 门类分面补名称（其余字段 value 即标签）
    facets = result.get("facets", {})
    cat_buckets = facets.get("category_id", [])
    name_map = await _category_names([str(b["value"]) for b in cat_buckets])
    out_facets = {}
    for name, buckets in facets.items():
        if name == "category_id":
            out_facets[name] = [
                {
                    "value": b["value"],
                    "count": b["count"],
                    "label": name_map.get(str(b["value"]), "未分类"),
                }
                for b in buckets
            ]
        else:
            out_facets[name] = [
                {"value": b["value"], "count": b["count"], "label": str(b["value"])}
                for b in buckets
            ]

    return success(
        {
            "total": result.get("total", 0),
            "hits": result.get("hits", []),
            "facets": out_facets,
            "facet_fields": list(FACET_FIELDS.keys()),
            "authed": current_user is not None,
            "error": result.get("error"),
        }
    )
