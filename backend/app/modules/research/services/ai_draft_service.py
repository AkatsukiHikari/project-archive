"""AI 辅助编研：按用户的写作要求生成编研文章（HTML），供插入文档。

提示词与模型在 Dify「编研起草」应用内维护，本服务仅组装资料并转发：
query=用户写作要求；inputs.es_context=成果档案库原文 + 按主题 ES 检索的馆藏原文。
API key 取 DIFY_API_KEY_RESEARCH，未配置时回落 DIFY_QA_API_KEY。
未配 key、AI 报错或无返回时抛 ValidationException，由调用方提示用户。
生成结果作为草稿插入编辑器，由编研人员核对润色后定稿。
"""

import html
import json
import logging
import re
import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.error_code import ErrorCode
from app.common.exceptions.base import NotFoundException
from app.core.config import settings
from app.modules.ai.services.dify_service import dify_service
from app.modules.research.models import (ResearchMaterial, ResearchResult,
                                         ResearchResultArchive)

logger = logging.getLogger(__name__)
MAX_ITEMS = 80


class AiDraftService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def draft(
        self,
        result_id: uuid.UUID,
        topic: Optional[str],
        user_id: uuid.UUID,
        tenant_id: Optional[uuid.UUID],
    ) -> dict:
        result = await self._get_result(result_id, tenant_id)
        # 优先专用 research key；未配则走问答 Chatflow（带 Dify 知识库检索节点）
        api_key = (
            settings.DIFY_API_KEY_RESEARCH
            or settings.DIFY_QA_API_KEY
            or settings.DIFY_API_KEY
        )
        if not api_key:
            raise ValidationException(message="未配置 AI 服务（DIFY_QA_API_KEY），无法起草")

        items = await self._load_items(result, tenant_id)
        # 有主题时：按主题从馆藏(ES)检索相关档案原文，扩充参考资料
        if topic:
            items = items + await self._search_related(topic, items, tenant_id)
        listing = (
            self._build_listing(items)
            if items
            else "（本成果尚未选定档案，请主要依据知识库召回内容撰写）"
        )

        ask = (topic or "").strip() or f"围绕成果《{result.title}》撰写一篇编研文章"
        answer = (
            await self._collect(
                ask,
                user_id,
                api_key,
                {
                    "es_context": listing,
                    "title": result.title or "",
                    "result_type": result.result_type or "",
                },
            )
        ).strip()
        if not answer:
            raise ValidationException(message="AI 未返回内容，请稍后重试")

        summary = None
        body = answer
        m = re.search(r"提要[:：]\s*(.+)", answer)
        if m:
            summary = m.group(1).split("\n")[0].strip()
            body = answer[m.end() :].strip() or answer
        return {"summary": summary, "content": self._md_to_html(body)}

    # ── 上下文：档案条目 + 真实原文摘录（控制总长）──────────────────────────────

    @staticmethod
    def _build_listing(items: list[dict]) -> str:
        clip, budget = 600, 28000
        used = 0
        parts: list[str] = []
        for i, it in enumerate(items):
            head = (
                f"{i + 1}. 〔{it['DH'] or '无档号'}〕{it['TM']}"
                f"（{it['WJRQ'] or it['ND'] or '日期不详'}，责任者 {it['RZZ'] or '不详'}）"
            )
            ft = (it.get("full_text") or "").strip()
            if ft and used < budget:
                seg = ft[:clip]
                used += len(seg)
                parts.append(head + "\n   原文：" + seg + ("…" if len(ft) > clip else ""))
            else:
                parts.append(head + "\n   （仅条目信息，暂无数字化原文）")
        return "\n\n".join(parts)

    # ── Dify 流式收集 ────────────────────────────────────────────────────────────

    async def _collect(
        self,
        query: str,
        user_id: uuid.UUID,
        api_key: str,
        inputs: Optional[dict] = None,
    ) -> str:
        parts: list[str] = []
        async for line in dify_service.stream_chat(
            query=query,
            user_id=str(user_id),
            scenario_code="research",
            api_key=api_key,
            inputs=inputs or {},
        ):
            line = line.strip()
            if not line.startswith("data:"):
                continue
            try:
                event = json.loads(line[5:].strip())
            except json.JSONDecodeError:
                continue
            if event.get("event") == "error":
                raise ValidationException(
                    message=f"AI 服务错误：{event.get('message') or '生成失败'}"
                )
            if event.get("event") in ("message", "agent_message"):
                parts.append(event.get("answer") or "")
        return "".join(parts)

    # ── 数据加载 ────────────────────────────────────────────────────────────────

    async def _get_result(
        self, result_id: uuid.UUID, tenant_id: Optional[uuid.UUID]
    ) -> ResearchResult:
        stmt = select(ResearchResult).where(
            ResearchResult.id == result_id, ResearchResult.is_deleted.is_(False)
        )
        if tenant_id:
            stmt = stmt.where(ResearchResult.tenant_id == tenant_id)
        r = (await self.db.execute(stmt)).scalars().first()
        if not r:
            raise NotFoundException(
                code=ErrorCode.RESEARCH_RESULT_NOT_FOUND, message="编研成果不存在"
            )
        return r

    async def _load_items(
        self, result: ResearchResult, tenant_id: Optional[uuid.UUID]
    ) -> list[dict]:
        archives = (
            (
                await self.db.execute(
                    select(ResearchResultArchive)
                    .where(
                        ResearchResultArchive.result_id == result.id,
                        ResearchResultArchive.is_deleted.is_(False),
                    )
                    .order_by(ResearchResultArchive.WJRQ.asc().nulls_last())
                    .limit(MAX_ITEMS)
                )
            )
            .scalars()
            .all()
        )
        if not archives and result.project_id:
            archives = (
                (
                    await self.db.execute(
                        select(ResearchMaterial)
                        .where(
                            ResearchMaterial.project_id == result.project_id,
                            ResearchMaterial.is_deleted.is_(False),
                        )
                        .order_by(ResearchMaterial.WJRQ.asc().nulls_last())
                        .limit(MAX_ITEMS)
                    )
                )
                .scalars()
                .all()
            )
        items = [
            {
                "archive_id": getattr(a, "archive_id", None),
                "DH": a.DH, "TM": a.TM, "RZZ": a.RZZ, "ND": a.ND, "WJRQ": a.WJRQ,
                "full_text": "",
            }
            for a in archives
        ]
        # 从原档案取真实全文（知识库内容），供 AI 基于原文撰写而非凭题名瞎编
        texts = await self._fetch_full_texts(
            [it["archive_id"] for it in items if it["archive_id"]]
        )
        for it in items:
            it["full_text"] = texts.get(str(it["archive_id"]), "")
        return items

    async def _search_related(
        self, topic: str, existing: list[dict], tenant_id: Optional[uuid.UUID]
    ) -> list[dict]:
        """按主题从馆藏检索相关档案（含原文），扩充编研参考资料。"""
        from app.infra.search.archive_index import super_search

        try:
            r = await super_search(
                keyword=topic,
                mode="qa",
                tenant_id=str(tenant_id) if tenant_id else None,
                include_staging=True,
                limit=8,
            )
        except Exception:  # noqa: BLE001
            return []
        seen = {it.get("DH") for it in existing if it.get("DH")}
        out: list[dict] = []
        for h in r.get("hits", []):
            if h.get("DH") in seen:
                continue
            out.append(
                {
                    "archive_id": None,
                    "DH": h.get("DH"), "TM": h.get("TM") or "",
                    "RZZ": h.get("RZZ"), "ND": h.get("ND"), "WJRQ": h.get("WJRQ"),
                    "full_text": h.get("full_text") or "",
                }
            )
        return out

    async def _fetch_full_texts(self, archive_ids: list) -> dict:
        from app.modules.repository.models.archive import (Archive,
                                                           ArchiveStaging)

        out: dict = {}
        if not archive_ids:
            return out
        for model in (Archive, ArchiveStaging):
            rows = (
                await self.db.execute(
                    select(model.id, model.full_text).where(model.id.in_(archive_ids))
                )
            ).all()
            for aid, ft in rows:
                if ft and str(aid) not in out:
                    out[str(aid)] = ft
        return out

    @staticmethod
    def _md_to_html(text: str) -> str:
        """极简 Markdown→HTML：标题、加粗、列表、空行分段。正文仍可在编辑器里调整。"""

        def inline(s: str) -> str:
            s = html.escape(s)
            return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)

        blocks = [b.strip() for b in re.split(r"\n\s*\n", text) if b.strip()]
        out: list[str] = []
        for b in blocks:
            heading = re.match(r"^(#{1,3})\s+(.*)$", b)
            if heading:
                level = len(heading.group(1)) + 1  # # -> h2, ## -> h3
                out.append(f"<h{level}>{inline(heading.group(2))}</h{level}>")
                continue
            lines = b.split("\n")
            if all(re.match(r"^\s*[-*]\s+", ln) for ln in lines):
                stripped = [re.sub(r"^\s*[-*]\s+", "", ln) for ln in lines]
                lis = "".join(f"<li>{inline(s)}</li>" for s in stripped)
                out.append(f"<ul>{lis}</ul>")
            else:
                out.append(f"<p>{inline(b)}</p>")
        return "".join(out)
