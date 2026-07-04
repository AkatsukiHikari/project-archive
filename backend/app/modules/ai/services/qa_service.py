"""档案问答 / AI 解读。

核心原则（与设计一致）：**检索由后端 ES 负责（准），合成由 DeepSeek 负责（顺）**。
- chat：用 ES（超级查询）检索相关档案及其原文，作为上下文交给模型作答、带档号引用。
- interpret：解读单份档案——直接把该档案完整信息（元数据 + 全文）喂模型，不走检索。

模型经 Dify（DeepSeek 为文本模型）。stream_chat 直接产出 SSE，透传给前端。
"""

import uuid
from typing import AsyncGenerator, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.infra.search.archive_index import super_search
from app.modules.ai.services.dify_service import dify_service
from app.modules.repository.models.archive import Archive, ArchiveStaging
from app.modules.repository.models.category import ArchiveCategory

MAX_CONTEXT_ARCHIVES = 6
FULLTEXT_CLIP = 1200

# 统计/计数类问题：RAG 只能取 top-K 样本，无法计数，必须走后端精确聚合
STATS_KEYWORDS = (
    "统计",
    "多少",
    "数量",
    "总数",
    "总共",
    "合计",
    "几件",
    "几条",
    "分布",
    "占比",
    "比例",
    "按全宗",
    "按年度",
    "按门类",
    "按密级",
    "列出所有",
    "全部档案",
    "所有档案",
    "总件数",
    "报表",
    "图表",
    "柱状图",
    "饼图",
    "折线图",
    "趋势",
    "可视化",
)
# 聚合维度：(列名, 中文标签)。正式库含开放状态；暂存库无 KFZT 字段。
STATS_DIMS = (
    ("QZH", "按全宗（QZH）"),
    ("ND", "按年度（ND）"),
    ("MJ", "按密级（MJ）"),
    ("BGQX", "按保管期限（BGQX）"),
    ("KFZT", "按开放状态（KFZT）"),
)
STATS_DIMS_STAGING = tuple(d for d in STATS_DIMS if d[0] != "KFZT")


def _is_stats_query(query: str) -> bool:
    return any(kw in query for kw in STATS_KEYWORDS)


def _qa_key() -> Optional[str]:
    # 问答 Chatflow（知识库检索 + DeepSeek）
    return settings.DIFY_QA_API_KEY or settings.DIFY_API_KEY or None


class QaService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ── 档案问答（ES 检索 + 模型合成）──────────────────────────────────────────

    async def chat(
        self,
        query: str,
        user_id: uuid.UUID,
        tenant_id: Optional[uuid.UUID],
        conversation_id: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        # 统计/计数类问题：走后端精确聚合（RAG 取样本无法计数）
        citations_event: Optional[str] = None
        if _is_stats_query(query):
            context = await self._stats_context(tenant_id)
        else:
            result = await super_search(
                keyword=query,
                mode="qa",  # 综合检索：档号/题名/全文/责任者/全宗/年度/密级 全覆盖
                tenant_id=str(tenant_id) if tenant_id else None,
                include_staging=True,  # 正式库 + 暂存库都检索，命中按来源标注
                limit=MAX_CONTEXT_ARCHIVES,
            )
            hits = result.get("hits", [])
            if not hits:
                yield _sse_answer(
                    "没有检索到与该问题相关的馆藏档案。请换个说法，或确认档案是否已归档。"
                )
                return
            context = (
                "【以下为后端检索到的相关档案，含正式库与暂存库；"
                "回答时请据实标明每条来自『正式库』还是『暂存库（整理中）』】\n\n"
                + "\n\n".join(self._hit_block(i + 1, h) for i, h in enumerate(hits))
            )
            citations_event = _citations_sse(hits)

        # 先推命中档案为可点击引用（前端 chip → 点击带档号去查阅页自动检索）
        if citations_event:
            yield citations_event

        # 用户问句原样作 query（Chatflow 的知识检索基于它召回），精确数据作 es_context
        async for line in dify_service.stream_chat(
            query=query,
            user_id=str(user_id),
            conversation_id=conversation_id,
            scenario_code="qa",
            api_key=_qa_key(),
            inputs={"es_context": context},
        ):
            yield line

    # ── 统计（后端精确聚合，正式库 + 暂存库，供统计/计数类问题作答）──────────────

    async def _stats_context(self, tenant_id: Optional[uuid.UUID]) -> str:
        formal_block, formal_total = await self._lib_stats(
            Archive, "正式库（已归档馆藏）", STATS_DIMS, tenant_id
        )
        staging_block, staging_total = await self._lib_stats(
            ArchiveStaging,
            "暂存库（著录整理中、未正式归档）",
            STATS_DIMS_STAGING,
            tenant_id,
        )
        return (
            "【档案统计（后端实时精确统计，权威数据）\n"
            "请严格依据以下数字作答，不要自行数数、估算或编造；\n"
            "回答时务必区分『正式库』与『暂存库』两类来源，不要混为一谈；\n"
            "若问题维度不在下列统计中，请如实说明暂未统计该维度】\n\n"
            f"全部合计：{formal_total + staging_total} 件"
            f"（正式库 {formal_total} 件 + 暂存库 {staging_total} 件）\n\n"
            f"{formal_block}\n\n{staging_block}"
        )

    async def _lib_stats(
        self, model, src_label: str, dims, tenant_id: Optional[uuid.UUID]
    ) -> tuple[str, int]:
        conds = [model.is_deleted.is_(False)]
        if tenant_id:
            conds.append(model.tenant_id == tenant_id)

        total = (
            await self.db.execute(select(func.count()).select_from(model).where(*conds))
        ).scalar_one()

        lines = [f"=== {src_label}：{total} 件 ==="]
        for col, label in dims:
            column = getattr(model, col)
            rows = (
                await self.db.execute(
                    select(column, func.count())
                    .where(*conds)
                    .group_by(column)
                    .order_by(func.count().desc())
                )
            ).all()
            if not rows:
                continue
            lines.append(f"{label}：")
            for val, cnt in rows[:60]:
                shown = val if val not in (None, "") else "（空）"
                lines.append(f"  {shown}：{cnt} 件")

        cat_rows = (
            await self.db.execute(
                select(ArchiveCategory.name, func.count())
                .select_from(model)
                .join(ArchiveCategory, ArchiveCategory.id == model.category_id)
                .where(*conds)
                .group_by(ArchiveCategory.name)
                .order_by(func.count().desc())
            )
        ).all()
        if cat_rows:
            lines.append("按门类：")
            for name, cnt in cat_rows[:60]:
                lines.append(f"  {name}：{cnt} 件")
        return "\n".join(lines), total

    # ── 解读单份档案（喂完整信息）──────────────────────────────────────────────

    async def interpret(
        self,
        archive_id: uuid.UUID,
        user_id: uuid.UUID,
        tenant_id: Optional[uuid.UUID],
    ) -> AsyncGenerator[str, None]:
        archive = await self._load_archive(archive_id, tenant_id)
        if archive is None:
            yield _sse_answer("未找到该档案。")
            return
        async for line in dify_service.stream_chat(
            query="请基于提供的这份档案，解读它的核心内容、形成背景、价值与利用要点。",
            user_id=str(user_id),
            scenario_code="qa",
            api_key=_qa_key(),
            inputs={"es_context": self._archive_full_block(archive)},
        ):
            yield line

    # ── 内部 ──────────────────────────────────────────────────────────────────

    @staticmethod
    def _hit_block(idx: int, h: dict) -> str:
        ft = (h.get("full_text") or "").strip()
        ft = (
            ft[:FULLTEXT_CLIP] + ("…" if len(ft) > FULLTEXT_CLIP else "")
            if ft
            else "（无原文）"
        )
        src = "暂存库（整理中）" if h.get("doc_source") == "staging" else "正式库"
        return (
            f"{idx}. 〔{src}〕〔{h.get('DH') or '无档号'}〕{h.get('TM') or ''}"
            f"（{h.get('ND') or '年度不详'}，全宗 {h.get('QZH') or '?'}，责任者 {h.get('RZZ') or '不详'}）\n"
            f"   原文摘录：{ft}"
        )

    @staticmethod
    def _archive_full_block(a) -> str:
        ft = (a.full_text or "").strip() or "（该档案暂无数字化原文/OCR 全文）"
        return (
            f"档号：{a.DH or '—'}\n题名：{a.TM}\n责任者：{a.RZZ or '—'}\n"
            f"年度：{a.ND or '—'}　全宗号：{a.QZH or '—'}\n"
            f"密级：{a.MJ or '—'}　保管期限：{a.BGQX or '—'}\n"
            f"文件日期：{a.WJRQ or '—'}\n\n【原文】\n{ft}"
        )

    async def _load_archive(
        self, archive_id: uuid.UUID, tenant_id: Optional[uuid.UUID]
    ):
        for model in (Archive, ArchiveStaging):
            stmt = select(model).where(
                model.id == archive_id, model.is_deleted.is_(False)
            )
            if tenant_id:
                stmt = stmt.where(model.tenant_id == tenant_id)
            obj = (await self.db.execute(stmt)).scalars().first()
            if obj:
                return obj
        return None


def _sse_answer(text: str) -> str:
    import json

    return (
        "data: "
        + json.dumps({"event": "message", "answer": text}, ensure_ascii=False)
        + "\n\n"
    )


def _citations_sse(hits: list[dict]) -> str:
    """把检索命中的档案转成前端可点击引用 chip（source_type=meta，extra 带档号）。"""
    import json

    chips = [
        {
            "chunk_id": str(h.get("id") or h.get("DH") or i),
            "source_type": "meta",
            "source_id": str(h.get("id") or ""),
            "title": f"〔{h.get('DH') or '无档号'}〕{h.get('TM') or ''}".strip(),
            "snippet": (h.get("full_text") or "")[:160],
            "score": float(h.get("score") or 0),
            "extra": {
                "DH": h.get("DH") or "",
                "doc_source": h.get("doc_source") or "",
            },
        }
        for i, h in enumerate(hits)
    ]
    return (
        "data: "
        + json.dumps({"event": "citations", "citations": chips}, ensure_ascii=False)
        + "\n\n"
    )
