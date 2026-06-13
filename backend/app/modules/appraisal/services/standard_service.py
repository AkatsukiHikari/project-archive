"""鉴定标准条款 / 敏感词库 维护。"""

import uuid
from typing import Optional

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.error_code import ErrorCode
from app.common.exceptions.base import NotFoundException, ValidationException
from app.modules.appraisal.models import (AppraisalSensitiveWord,
                                          AppraisalStandard)
from app.modules.appraisal.schemas.standard import (SensitiveWordCreate,
                                                    SensitiveWordUpdate,
                                                    StandardCreate,
                                                    StandardUpdate)


class StandardService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ── 标准条款 ──────────────────────────────────────────────────────────────

    async def list_standards(
        self, tenant_id: Optional[uuid.UUID], enabled_only: bool = False
    ) -> list[AppraisalStandard]:
        stmt = select(AppraisalStandard).where(AppraisalStandard.is_deleted.is_(False))
        if tenant_id:
            stmt = stmt.where(
                or_(
                    AppraisalStandard.tenant_id == tenant_id,
                    AppraisalStandard.tenant_id.is_(None),
                )
            )
        if enabled_only:
            stmt = stmt.where(AppraisalStandard.is_enabled.is_(True))
        stmt = stmt.order_by(AppraisalStandard.sort_order, AppraisalStandard.code)
        return list((await self.db.execute(stmt)).scalars())

    async def create_standard(
        self, body: StandardCreate, user_id: uuid.UUID, tenant_id: Optional[uuid.UUID]
    ) -> AppraisalStandard:
        await self._assert_code_free(body.code, tenant_id)
        standard = AppraisalStandard(
            **body.model_dump(), tenant_id=tenant_id, create_by=user_id
        )
        self.db.add(standard)
        await self.db.flush()
        return standard

    async def update_standard(
        self,
        standard_id: uuid.UUID,
        body: StandardUpdate,
        tenant_id: Optional[uuid.UUID],
    ) -> AppraisalStandard:
        standard = await self._require_standard(standard_id, tenant_id)
        for field, value in body.model_dump(exclude_unset=True).items():
            setattr(standard, field, value)
        await self.db.flush()
        return standard

    async def delete_standard(
        self, standard_id: uuid.UUID, tenant_id: Optional[uuid.UUID]
    ) -> None:
        standard = await self._require_standard(standard_id, tenant_id)
        standard.is_deleted = True

    async def _require_standard(
        self, standard_id: uuid.UUID, tenant_id: Optional[uuid.UUID]
    ) -> AppraisalStandard:
        stmt = select(AppraisalStandard).where(
            AppraisalStandard.id == standard_id, AppraisalStandard.is_deleted.is_(False)
        )
        if tenant_id:
            stmt = stmt.where(AppraisalStandard.tenant_id == tenant_id)
        standard = (await self.db.execute(stmt)).scalars().first()
        if not standard:
            raise NotFoundException(
                code=ErrorCode.APPRAISAL_STANDARD_NOT_FOUND, message="标准条款不存在"
            )
        return standard

    async def _assert_code_free(
        self, code: str, tenant_id: Optional[uuid.UUID]
    ) -> None:
        stmt = (
            select(func.count())
            .select_from(AppraisalStandard)
            .where(
                AppraisalStandard.code == code, AppraisalStandard.is_deleted.is_(False)
            )
        )
        if tenant_id:
            stmt = stmt.where(AppraisalStandard.tenant_id == tenant_id)
        if (await self.db.execute(stmt)).scalar_one():
            raise ValidationException(message=f"条款编码 {code} 已存在")

    # ── 敏感词 ────────────────────────────────────────────────────────────────

    async def list_words(
        self,
        tenant_id: Optional[uuid.UUID],
        keyword: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[int, list[AppraisalSensitiveWord]]:
        stmt = select(AppraisalSensitiveWord).where(
            AppraisalSensitiveWord.is_deleted.is_(False)
        )
        if tenant_id:
            stmt = stmt.where(
                or_(
                    AppraisalSensitiveWord.tenant_id == tenant_id,
                    AppraisalSensitiveWord.tenant_id.is_(None),
                )
            )
        if keyword:
            stmt = stmt.where(AppraisalSensitiveWord.word.ilike(f"%{keyword}%"))
        total = (
            await self.db.execute(select(func.count()).select_from(stmt.subquery()))
        ).scalar_one()
        words = (
            (
                await self.db.execute(
                    stmt.order_by(AppraisalSensitiveWord.create_time.desc())
                    .offset(skip)
                    .limit(limit)
                )
            )
            .scalars()
            .all()
        )
        return total, list(words)

    async def create_word(
        self,
        body: SensitiveWordCreate,
        user_id: uuid.UUID,
        tenant_id: Optional[uuid.UUID],
    ) -> AppraisalSensitiveWord:
        existing = (
            await self.db.execute(
                select(func.count())
                .select_from(AppraisalSensitiveWord)
                .where(
                    AppraisalSensitiveWord.word == body.word,
                    AppraisalSensitiveWord.is_deleted.is_(False),
                    AppraisalSensitiveWord.tenant_id == tenant_id,
                )
            )
        ).scalar_one()
        if existing:
            raise ValidationException(message=f"敏感词「{body.word}」已存在")
        word = AppraisalSensitiveWord(
            **body.model_dump(), tenant_id=tenant_id, create_by=user_id
        )
        self.db.add(word)
        await self.db.flush()
        return word

    async def update_word(
        self,
        word_id: uuid.UUID,
        body: SensitiveWordUpdate,
        tenant_id: Optional[uuid.UUID],
    ) -> AppraisalSensitiveWord:
        word = await self._require_word(word_id, tenant_id)
        for field, value in body.model_dump(exclude_unset=True).items():
            setattr(word, field, value)
        await self.db.flush()
        return word

    async def delete_word(
        self, word_id: uuid.UUID, tenant_id: Optional[uuid.UUID]
    ) -> None:
        word = await self._require_word(word_id, tenant_id)
        word.is_deleted = True

    async def _require_word(
        self, word_id: uuid.UUID, tenant_id: Optional[uuid.UUID]
    ) -> AppraisalSensitiveWord:
        stmt = select(AppraisalSensitiveWord).where(
            AppraisalSensitiveWord.id == word_id,
            AppraisalSensitiveWord.is_deleted.is_(False),
        )
        if tenant_id:
            stmt = stmt.where(AppraisalSensitiveWord.tenant_id == tenant_id)
        word = (await self.db.execute(stmt)).scalars().first()
        if not word:
            raise NotFoundException(
                code=ErrorCode.APPRAISAL_STANDARD_NOT_FOUND, message="敏感词不存在"
            )
        return word
