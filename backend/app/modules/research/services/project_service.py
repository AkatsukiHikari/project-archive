"""编研项目：立项、选材、查询。"""

import uuid
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.error_code import ErrorCode
from app.common.exceptions.base import NotFoundException
from app.modules.iam.models.user import User
from app.modules.research.models import (ResearchMaterial, ResearchProject,
                                         ResearchResult)
from app.modules.research.schemas.research import ProjectCreate, ProjectUpdate
from app.modules.research.services.snapshots import archive_snapshot


class ProjectService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ── 查询 ──────────────────────────────────────────────────────────────────

    async def list_projects(
        self, tenant_id: Optional[uuid.UUID], status: Optional[str] = None
    ) -> list[dict]:
        stmt = select(ResearchProject).where(ResearchProject.is_deleted.is_(False))
        if tenant_id:
            stmt = stmt.where(ResearchProject.tenant_id == tenant_id)
        if status:
            stmt = stmt.where(ResearchProject.status == status)
        projects = (
            (await self.db.execute(stmt.order_by(ResearchProject.create_time.desc())))
            .scalars()
            .all()
        )

        mat_counts = await self._count_by_project(
            ResearchMaterial, [p.id for p in projects]
        )
        res_counts = await self._count_by_project(
            ResearchResult, [p.id for p in projects]
        )
        names = await self._user_names(
            {p.editor_id for p in projects} | {p.reviewer_id for p in projects}
        )
        return [
            self._project_dict(
                p, names, mat_counts.get(p.id, 0), res_counts.get(p.id, 0)
            )
            for p in projects
        ]

    async def get_project(
        self, project_id: uuid.UUID, tenant_id: Optional[uuid.UUID]
    ) -> dict:
        p = await self._require(project_id, tenant_id)
        mat = await self._count_by_project(ResearchMaterial, [p.id])
        res = await self._count_by_project(ResearchResult, [p.id])
        names = await self._user_names({p.editor_id, p.reviewer_id})
        return self._project_dict(p, names, mat.get(p.id, 0), res.get(p.id, 0))

    async def create_project(
        self, body: ProjectCreate, user_id: uuid.UUID, tenant_id: Optional[uuid.UUID]
    ) -> ResearchProject:
        project = ResearchProject(
            **body.model_dump(),
            status="in_progress",
            tenant_id=tenant_id,
            create_by=user_id,
        )
        self.db.add(project)
        await self.db.flush()
        return project

    async def update_project(
        self, project_id: uuid.UUID, body: ProjectUpdate, tenant_id: Optional[uuid.UUID]
    ) -> ResearchProject:
        p = await self._require(project_id, tenant_id)
        for field, value in body.model_dump(exclude_unset=True).items():
            setattr(p, field, value)
        await self.db.flush()
        return p

    async def delete_project(
        self, project_id: uuid.UUID, tenant_id: Optional[uuid.UUID]
    ) -> None:
        p = await self._require(project_id, tenant_id)
        p.is_deleted = True

    # ── 选材 ──────────────────────────────────────────────────────────────────

    async def list_materials(
        self, project_id: uuid.UUID, tenant_id: Optional[uuid.UUID]
    ) -> list[ResearchMaterial]:
        await self._require(project_id, tenant_id)
        return list(
            (
                await self.db.execute(
                    select(ResearchMaterial)
                    .where(
                        ResearchMaterial.project_id == project_id,
                        ResearchMaterial.is_deleted.is_(False),
                    )
                    .order_by(
                        ResearchMaterial.WJRQ.asc().nulls_last(), ResearchMaterial.DH
                    )
                )
            ).scalars()
        )

    async def add_materials(
        self,
        project_id: uuid.UUID,
        archive_ids: list[uuid.UUID],
        tenant_id: Optional[uuid.UUID],
    ) -> int:
        await self._require(project_id, tenant_id)
        existing = set(
            (
                await self.db.execute(
                    select(ResearchMaterial.archive_id).where(
                        ResearchMaterial.project_id == project_id,
                        ResearchMaterial.is_deleted.is_(False),
                    )
                )
            )
            .scalars()
            .all()
        )

        # 源档案快照：先查暂存库，再查正式库
        added = 0
        for aid in archive_ids:
            if aid in existing:
                continue
            snap = await archive_snapshot(self.db, aid)
            if not snap:
                continue
            self.db.add(
                ResearchMaterial(
                    project_id=project_id, archive_id=aid, tenant_id=tenant_id, **snap
                )
            )
            added += 1
        await self.db.flush()
        return added

    async def remove_material(
        self, material_id: uuid.UUID, tenant_id: Optional[uuid.UUID]
    ) -> None:
        stmt = select(ResearchMaterial).where(
            ResearchMaterial.id == material_id, ResearchMaterial.is_deleted.is_(False)
        )
        if tenant_id:
            stmt = stmt.where(ResearchMaterial.tenant_id == tenant_id)
        m = (await self.db.execute(stmt)).scalars().first()
        if m:
            m.is_deleted = True

    # ── 内部 ──────────────────────────────────────────────────────────────────

    async def _require(
        self, project_id: uuid.UUID, tenant_id: Optional[uuid.UUID]
    ) -> ResearchProject:
        stmt = select(ResearchProject).where(
            ResearchProject.id == project_id, ResearchProject.is_deleted.is_(False)
        )
        if tenant_id:
            stmt = stmt.where(ResearchProject.tenant_id == tenant_id)
        p = (await self.db.execute(stmt)).scalars().first()
        if not p:
            raise NotFoundException(
                code=ErrorCode.RESEARCH_PROJECT_NOT_FOUND, message="编研项目不存在"
            )
        return p

    async def _count_by_project(self, model, project_ids: list[uuid.UUID]) -> dict:
        if not project_ids:
            return {}
        rows = (
            await self.db.execute(
                select(model.project_id, func.count())
                .where(model.project_id.in_(project_ids), model.is_deleted.is_(False))
                .group_by(model.project_id)
            )
        ).all()
        return {r[0]: r[1] for r in rows}

    async def _user_names(self, ids: set) -> dict[uuid.UUID, str]:
        ids = {i for i in ids if i}
        if not ids:
            return {}
        users = (
            (await self.db.execute(select(User).where(User.id.in_(ids))))
            .scalars()
            .all()
        )
        return {u.id: (u.full_name or u.username) for u in users}

    @staticmethod
    def _project_dict(p: ResearchProject, names: dict, mat: int, res: int) -> dict:
        return {
            "id": p.id,
            "title": p.title,
            "project_type": p.project_type,
            "editor_id": p.editor_id,
            "editor_name": names.get(p.editor_id),
            "reviewer_id": p.reviewer_id,
            "reviewer_name": names.get(p.reviewer_id),
            "members": p.members,
            "start_date": p.start_date,
            "end_date": p.end_date,
            "purpose": p.purpose,
            "status": p.status,
            "material_count": mat,
            "result_count": res,
            "create_time": p.create_time,
        }
