"""编研模板：内置 + 用户自存，供成果"快速开始"。"""

import uuid
from typing import Optional

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.error_code import ErrorCode
from app.common.exceptions.base import NotFoundException, ValidationException
from app.modules.research.models import ResearchTemplate
from app.modules.research.schemas.research import (TemplateCreate,
                                                   TemplateUpdate)


class TemplateService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_templates(
        self, tenant_id: Optional[uuid.UUID], result_type: Optional[str] = None
    ) -> list[ResearchTemplate]:
        stmt = select(ResearchTemplate).where(
            ResearchTemplate.is_deleted.is_(False),
            or_(
                ResearchTemplate.is_builtin.is_(True),
                ResearchTemplate.tenant_id == tenant_id,
            ),
        )
        if result_type:
            stmt = stmt.where(ResearchTemplate.result_type == result_type)
        return list(
            (
                await self.db.execute(
                    stmt.order_by(
                        ResearchTemplate.is_builtin.desc(),
                        ResearchTemplate.sort_order,
                        ResearchTemplate.create_time.desc(),
                    )
                )
            ).scalars()
        )

    async def get_template(
        self, template_id: uuid.UUID, tenant_id: Optional[uuid.UUID]
    ) -> ResearchTemplate:
        return await self._require(template_id, tenant_id)

    async def create_template(
        self, body: TemplateCreate, user_id: uuid.UUID, tenant_id: Optional[uuid.UUID]
    ) -> ResearchTemplate:
        tpl = ResearchTemplate(
            **body.model_dump(),
            is_builtin=False,
            tenant_id=tenant_id,
            create_by=user_id,
        )
        self.db.add(tpl)
        await self.db.flush()
        return tpl

    async def update_template(
        self,
        template_id: uuid.UUID,
        body: TemplateUpdate,
        tenant_id: Optional[uuid.UUID],
    ) -> ResearchTemplate:
        tpl = await self._require(template_id, tenant_id)
        if tpl.is_builtin:
            raise ValidationException(message="系统内置模板不可修改")
        for field, value in body.model_dump(exclude_unset=True).items():
            setattr(tpl, field, value)
        await self.db.flush()
        return tpl

    async def delete_template(
        self, template_id: uuid.UUID, tenant_id: Optional[uuid.UUID]
    ) -> None:
        tpl = await self._require(template_id, tenant_id)
        if tpl.is_builtin:
            raise ValidationException(message="系统内置模板不可删除")
        tpl.is_deleted = True

    async def _require(
        self, template_id: uuid.UUID, tenant_id: Optional[uuid.UUID]
    ) -> ResearchTemplate:
        tpl = (
            (
                await self.db.execute(
                    select(ResearchTemplate).where(
                        ResearchTemplate.id == template_id,
                        ResearchTemplate.is_deleted.is_(False),
                        or_(
                            ResearchTemplate.is_builtin.is_(True),
                            ResearchTemplate.tenant_id == tenant_id,
                        ),
                    )
                )
            )
            .scalars()
            .first()
        )
        if not tpl:
            raise NotFoundException(
                code=ErrorCode.RESEARCH_TEMPLATE_NOT_FOUND, message="编研模板不存在"
            )
        return tpl
