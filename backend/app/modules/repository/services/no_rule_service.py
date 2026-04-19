import uuid
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.error_code import ErrorCode
from app.common.exceptions.base import NotFoundException
from app.modules.repository.models.no_rule import ArchiveNoRule
from app.modules.repository.repositories.no_rule_repo import NoRuleRepository
from app.modules.repository.schemas.no_rule import NoRuleCreate, NoRuleUpdate


class NoRuleService:
    def __init__(self, db: AsyncSession) -> None:
        self._repo = NoRuleRepository(db)

    async def list_all(self, tenant_id: Optional[uuid.UUID] = None) -> list[ArchiveNoRule]:
        return await self._repo.list_by_tenant(tenant_id=tenant_id)

    async def get(self, rule_id: uuid.UUID) -> ArchiveNoRule:
        rule = await self._repo.get_by_id(rule_id)
        if not rule:
            raise NotFoundException(code=ErrorCode.ARCHIVE_NOT_FOUND, message="档号规则不存在")
        return rule

    async def create(
        self, data: NoRuleCreate, tenant_id: Optional[uuid.UUID]
    ) -> ArchiveNoRule:
        rule = ArchiveNoRule(
            category_id=data.category_id,
            name=data.name,
            rule_template=data.rule_template,
            seq_scope=data.seq_scope,
            is_active=data.is_active,
            tenant_id=tenant_id,
        )
        return await self._repo.create(rule)

    async def update(self, rule_id: uuid.UUID, data: NoRuleUpdate) -> ArchiveNoRule:
        rule = await self.get(rule_id)
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(rule, field, value)
        return rule

    async def delete(self, rule_id: uuid.UUID) -> None:
        rule = await self.get(rule_id)
        await self._repo.delete(rule)
