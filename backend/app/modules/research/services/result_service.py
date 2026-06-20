"""编研成果：富文档编纂、成果档案库、状态流转、大事记表格生成。"""

import html
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.error_code import ErrorCode
from app.common.exceptions.base import NotFoundException, ValidationException
from app.modules.research.models import (ResearchMaterial, ResearchProject,
                                         ResearchResult, ResearchResultArchive,
                                         ResearchTemplate)
from app.modules.research.schemas.research import ResultCreate, ResultUpdate
from app.modules.research.services.snapshots import archive_snapshot

LOCKED = ("finalized", "published")


class ResultService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ── 查询 ──────────────────────────────────────────────────────────────────

    async def list_results(
        self,
        tenant_id: Optional[uuid.UUID],
        result_type: Optional[str] = None,
        status: Optional[str] = None,
        project_id: Optional[uuid.UUID] = None,
        keyword: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[int, list[dict]]:
        stmt = (
            select(ResearchResult, ResearchProject.title)
            .outerjoin(ResearchProject, ResearchResult.project_id == ResearchProject.id)
            .where(ResearchResult.is_deleted.is_(False))
        )
        if tenant_id:
            stmt = stmt.where(ResearchResult.tenant_id == tenant_id)
        if result_type:
            stmt = stmt.where(ResearchResult.result_type == result_type)
        if status:
            stmt = stmt.where(ResearchResult.status == status)
        if project_id:
            stmt = stmt.where(ResearchResult.project_id == project_id)
        if keyword:
            stmt = stmt.where(ResearchResult.title.ilike(f"%{keyword}%"))

        total = (
            await self.db.execute(select(func.count()).select_from(stmt.subquery()))
        ).scalar_one()
        rows = (
            await self.db.execute(
                stmt.order_by(ResearchResult.create_time.desc())
                .offset(skip)
                .limit(limit)
            )
        ).all()
        counts = await self._archive_counts([r[0].id for r in rows])
        return total, [
            self._result_dict(r[0], r[1], counts.get(r[0].id, 0), with_content=False)
            for r in rows
        ]

    async def get_result(
        self, result_id: uuid.UUID, tenant_id: Optional[uuid.UUID]
    ) -> dict:
        r, project_title = await self._require(result_id, tenant_id)
        counts = await self._archive_counts([r.id])
        return self._result_dict(r, project_title, counts.get(r.id, 0))

    # ── 增删改 ────────────────────────────────────────────────────────────────

    async def create_result(
        self, body: ResultCreate, user_id: uuid.UUID, tenant_id: Optional[uuid.UUID]
    ) -> ResearchResult:
        content = body.content
        content_json = body.content_json
        if body.template_id and content is None and content_json is None:
            tpl = await self._get_template(body.template_id, tenant_id)
            if tpl:
                content = tpl.content
                content_json = tpl.content_json
        result = ResearchResult(
            project_id=body.project_id,
            title=body.title,
            result_type=body.result_type,
            summary=body.summary,
            content=content,
            content_json=content_json,
            status="draft",
            author_id=user_id,
            tenant_id=tenant_id,
            create_by=user_id,
        )
        self.db.add(result)
        await self.db.flush()
        return result

    async def update_result(
        self, result_id: uuid.UUID, body: ResultUpdate, tenant_id: Optional[uuid.UUID]
    ) -> ResearchResult:
        r, _ = await self._require(result_id, tenant_id)
        if r.status in LOCKED:
            raise ValidationException(
                code=ErrorCode.RESEARCH_STATE_CONFLICT,
                message="成果已定稿/发布，请先撤回再编辑",
            )
        for field, value in body.model_dump(exclude_unset=True).items():
            setattr(r, field, value)
        await self.db.flush()
        return r

    async def delete_result(
        self, result_id: uuid.UUID, tenant_id: Optional[uuid.UUID]
    ) -> None:
        r, _ = await self._require(result_id, tenant_id)
        r.is_deleted = True

    # ── 状态流转 ──────────────────────────────────────────────────────────────

    async def transition(
        self,
        result_id: uuid.UUID,
        action: str,
        user_id: uuid.UUID,
        tenant_id: Optional[uuid.UUID],
    ) -> ResearchResult:
        r, _ = await self._require(result_id, tenant_id)
        now = datetime.now(timezone.utc)
        flow = {
            "submit": ("draft", "reviewing", {}),
            "finalize": (
                "reviewing",
                "finalized",
                {"reviewer_id": user_id, "finalized_at": now},
            ),
            "publish": ("finalized", "published", {"published_at": now}),
            "reopen": (None, "draft", {"finalized_at": None, "published_at": None}),
        }
        if action not in flow:
            raise ValidationException(message="未知操作")
        need, target, extra = flow[action]
        if need is not None and r.status != need:
            raise ValidationException(
                code=ErrorCode.RESEARCH_STATE_CONFLICT,
                message=f"当前状态不允许该操作（需 {need}）",
            )
        r.status = target
        for k, v in extra.items():
            setattr(r, k, v)
        await self.db.flush()
        return r

    # ── 成果档案库 ────────────────────────────────────────────────────────────

    async def list_archives(
        self, result_id: uuid.UUID, tenant_id: Optional[uuid.UUID]
    ) -> list[ResearchResultArchive]:
        await self._require(result_id, tenant_id)
        return list(
            (
                await self.db.execute(
                    select(ResearchResultArchive)
                    .where(
                        ResearchResultArchive.result_id == result_id,
                        ResearchResultArchive.is_deleted.is_(False),
                    )
                    .order_by(
                        ResearchResultArchive.sort_order,
                        ResearchResultArchive.WJRQ.asc().nulls_last(),
                    )
                )
            ).scalars()
        )

    async def add_archives(
        self,
        result_id: uuid.UUID,
        archive_ids: Optional[list[uuid.UUID]],
        from_project: bool,
        tenant_id: Optional[uuid.UUID],
    ) -> int:
        r, _ = await self._require(result_id, tenant_id)
        ids: list[uuid.UUID] = list(archive_ids or [])
        if from_project and r.project_id:
            mats = (
                (
                    await self.db.execute(
                        select(ResearchMaterial.archive_id).where(
                            ResearchMaterial.project_id == r.project_id,
                            ResearchMaterial.is_deleted.is_(False),
                        )
                    )
                )
                .scalars()
                .all()
            )
            ids.extend(mats)

        existing = set(
            (
                await self.db.execute(
                    select(ResearchResultArchive.archive_id).where(
                        ResearchResultArchive.result_id == result_id,
                        ResearchResultArchive.is_deleted.is_(False),
                    )
                )
            )
            .scalars()
            .all()
        )
        base = await self._max_sort(result_id)
        added = 0
        for aid in dict.fromkeys(ids):  # 去重保序
            if aid in existing:
                continue
            snap = await archive_snapshot(self.db, aid)
            if not snap:
                continue
            base += 1
            self.db.add(
                ResearchResultArchive(
                    result_id=result_id,
                    archive_id=aid,
                    sort_order=base,
                    tenant_id=tenant_id,
                    **snap,
                )
            )
            added += 1
        await self.db.flush()
        return added

    async def remove_archive(
        self, ra_id: uuid.UUID, tenant_id: Optional[uuid.UUID]
    ) -> None:
        stmt = select(ResearchResultArchive).where(
            ResearchResultArchive.id == ra_id,
            ResearchResultArchive.is_deleted.is_(False),
        )
        if tenant_id:
            stmt = stmt.where(ResearchResultArchive.tenant_id == tenant_id)
        ra = (await self.db.execute(stmt)).scalars().first()
        if ra:
            ra.is_deleted = True

    # ── 大事记表格：从成果档案库按日期生成 HTML（不走 AI）──────────────────────────

    async def chronicle_html(
        self, result_id: uuid.UUID, tenant_id: Optional[uuid.UUID]
    ) -> str:
        archives = await self.list_archives(result_id, tenant_id)
        archives = sorted(
            archives, key=lambda a: (a.WJRQ or str(a.ND or ""), a.DH or "")
        )
        rows = "".join(
            "<tr>"
            f"<td>{html.escape(a.WJRQ or (str(a.ND) if a.ND else ''))}</td>"
            f"<td>{html.escape(a.TM)}</td>"
            f"<td>{html.escape(a.DH or '')}</td>"
            "</tr>"
            for a in archives
        )
        return (
            "<table><thead><tr>"
            "<th>日期</th><th>大事记事</th><th>来源档号</th>"
            "</tr></thead><tbody>"
            + (rows or "<tr><td colspan='3'>暂无档案，请先建立成果档案库</td></tr>")
            + "</tbody></table>"
        )

    # ── 内部 ──────────────────────────────────────────────────────────────────

    async def _require(
        self, result_id: uuid.UUID, tenant_id: Optional[uuid.UUID]
    ) -> tuple[ResearchResult, Optional[str]]:
        stmt = (
            select(ResearchResult, ResearchProject.title)
            .outerjoin(ResearchProject, ResearchResult.project_id == ResearchProject.id)
            .where(ResearchResult.id == result_id, ResearchResult.is_deleted.is_(False))
        )
        if tenant_id:
            stmt = stmt.where(ResearchResult.tenant_id == tenant_id)
        row = (await self.db.execute(stmt)).first()
        if not row:
            raise NotFoundException(
                code=ErrorCode.RESEARCH_RESULT_NOT_FOUND, message="编研成果不存在"
            )
        return row[0], row[1]

    async def _get_template(
        self, template_id: uuid.UUID, tenant_id: Optional[uuid.UUID]
    ) -> Optional[ResearchTemplate]:
        # 模板：内置（tenant 为空）或本租户的
        return (
            (
                await self.db.execute(
                    select(ResearchTemplate).where(
                        ResearchTemplate.id == template_id,
                        ResearchTemplate.is_deleted.is_(False),
                    )
                )
            )
            .scalars()
            .first()
        )

    async def _archive_counts(self, result_ids: list[uuid.UUID]) -> dict:
        if not result_ids:
            return {}
        rows = (
            await self.db.execute(
                select(ResearchResultArchive.result_id, func.count())
                .where(
                    ResearchResultArchive.result_id.in_(result_ids),
                    ResearchResultArchive.is_deleted.is_(False),
                )
                .group_by(ResearchResultArchive.result_id)
            )
        ).all()
        return {r[0]: r[1] for r in rows}

    async def _max_sort(self, result_id: uuid.UUID) -> int:
        val = (
            await self.db.execute(
                select(
                    func.coalesce(func.max(ResearchResultArchive.sort_order), 0)
                ).where(
                    ResearchResultArchive.result_id == result_id,
                    ResearchResultArchive.is_deleted.is_(False),
                )
            )
        ).scalar_one()
        return int(val)

    @staticmethod
    def _result_dict(
        r: ResearchResult,
        project_title: Optional[str],
        archive_count: int,
        with_content: bool = True,
    ) -> dict:
        data = {
            "id": r.id,
            "project_id": r.project_id,
            "project_title": project_title,
            "title": r.title,
            "result_type": r.result_type,
            "summary": r.summary,
            "status": r.status,
            "author_id": r.author_id,
            "reviewer_id": r.reviewer_id,
            "finalized_at": r.finalized_at,
            "published_at": r.published_at,
            "archive_count": archive_count,
            "create_time": r.create_time,
        }
        if with_content:
            data["content"] = r.content
            data["content_json"] = r.content_json
        return data
