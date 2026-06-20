"""AI 辅助编研：基于成果档案库生成可插入文档的 HTML 片段。

走 Dify（scenario=research，DIFY_API_KEY_RESEARCH 回落 DIFY_API_KEY）。
结果只作为草稿插入编辑器，由编研人员核对润色——人工把关，AI 不直接定稿。
未配置 Dify key 时给出按档案整理的兜底 HTML（大事记表格 / 素材清单）。
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
        items = await self._load_items(result, tenant_id)
        if not items:
            return {
                "summary": None,
                "content": "<p>请先为本成果建立档案库（从馆藏选档或导入项目素材）。</p>",
            }

        result_type = result.result_type
        api_key = settings.dify_api_key_for("research")
        if not api_key:
            return self._fallback(result_type, items)

        listing = "\n".join(
            f"{i + 1}. 日期：{it['WJRQ'] or it['ND'] or '不详'}"
            f"｜题名：{it['TM']}｜责任者：{it['RZZ'] or '不详'}｜档号：{it['DH'] or '不详'}"
            for i, it in enumerate(items)
        )
        try:
            if result_type == "大事记":
                return await self._draft_chronicle(
                    listing, topic, user_id, api_key, items
                )
            return await self._draft_prose(
                result_type, listing, topic, user_id, api_key, items
            )
        except Exception:
            logger.exception("AI 编研拟稿失败 result=%s", result_id)
            return self._fallback(result_type, items)

    # ── 大事记：要 AI 返回 JSON 数组，再渲染成 HTML 表格 ──────────────────────────

    async def _draft_chronicle(
        self,
        listing: str,
        topic: Optional[str],
        user_id: uuid.UUID,
        api_key: str,
        items: list,
    ) -> dict:
        query = (
            "你是档案编研专家。根据以下档案条目编写一份大事记，按时间顺序，每条用简洁规范的"
            "书面语概括事件。\n"
            + (f"编研主题聚焦：{topic}\n" if topic else "")
            + f"\n档案条目：\n{listing}\n\n"
            "只输出 JSON 数组，不要其他文字。每个元素："
            '{"date": "YYYY-MM-DD 或 年份", "event": "事件简述", "source_dh": "来源档号(可空)"}'
        )
        entries = self._parse_json_array(await self._collect(query, user_id, api_key))
        clean = [e for e in entries if e.get("event")]
        if not clean:
            return self._fallback("大事记", items)
        rows = "".join(
            "<tr>"
            f"<td>{html.escape(str(e.get('date', '')))}</td>"
            f"<td>{html.escape(str(e.get('event', '')))}</td>"
            f"<td>{html.escape(str(e.get('source_dh', '')))}</td>"
            "</tr>"
            for e in clean
        )
        table = (
            "<table><thead><tr><th>日期</th><th>大事记事</th><th>来源档号</th></tr></thead>"
            f"<tbody>{rows}</tbody></table>"
        )
        return {"summary": None, "content": table}

    # ── 其它体裁：提要 + 正文 HTML ───────────────────────────────────────────────

    async def _draft_prose(
        self,
        result_type: str,
        listing: str,
        topic: Optional[str],
        user_id: uuid.UUID,
        api_key: str,
        items: list,
    ) -> dict:
        query = (
            f"你是档案编研专家。根据以下馆藏档案条目，撰写一份《{result_type}》初稿，"
            "语言规范、客观、有条理，分章节，用 Markdown 小标题（##）组织。\n"
            + (f"编研主题：{topic}\n" if topic else "")
            + f"\n档案条目：\n{listing}\n\n"
            "先写一句内容提要（以「提要：」开头），空一行后写正文。"
        )
        answer = (await self._collect(query, user_id, api_key)).strip()
        if not answer:
            return self._fallback(result_type, items)
        summary = None
        body = answer
        m = re.search(r"提要[:：]\s*(.+)", answer)
        if m:
            summary = m.group(1).split("\n")[0].strip()
            body = answer[m.end() :].strip() or answer
        return {"summary": summary, "content": self._md_to_html(body)}

    # ── Dify 流式收集 ────────────────────────────────────────────────────────────

    async def _collect(self, query: str, user_id: uuid.UUID, api_key: str) -> str:
        parts: list[str] = []
        async for line in dify_service.stream_chat(
            query=query, user_id=str(user_id), scenario_code="research", api_key=api_key
        ):
            line = line.strip()
            if not line.startswith("data:"):
                continue
            try:
                event = json.loads(line[5:].strip())
            except json.JSONDecodeError:
                continue
            if event.get("event") == "error":
                return ""
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
        return [
            {"DH": a.DH, "TM": a.TM, "RZZ": a.RZZ, "ND": a.ND, "WJRQ": a.WJRQ}
            for a in archives
        ]

    # ── 兜底（无 Dify key）──────────────────────────────────────────────────────

    @staticmethod
    def _fallback(result_type: str, items: list) -> dict:
        if result_type == "大事记":
            rows = "".join(
                "<tr>"
                f"<td>{html.escape(it['WJRQ'] or (str(it['ND']) if it['ND'] else ''))}</td>"
                f"<td>{html.escape(it['TM'])}</td>"
                f"<td>{html.escape(it['DH'] or '')}</td>"
                "</tr>"
                for it in items
            )
            table = (
                "<table><thead><tr><th>日期</th><th>大事记事</th><th>来源档号</th></tr></thead>"
                f"<tbody>{rows}</tbody></table>"
            )
            return {"summary": None, "content": table}
        lis = "".join(
            f"<li>{html.escape(it['TM'])}（{html.escape(it['WJRQ'] or str(it['ND'] or '不详'))}）</li>"
            for it in items
        )
        content = (
            f"<h2>{html.escape(result_type)}</h2>"
            f"<p>基于 {len(items)} 件馆藏档案整理的素材清单（AI 未启用，供编写参考）：</p>"
            f"<ul>{lis}</ul>"
        )
        return {"summary": None, "content": content}

    @staticmethod
    def _parse_json_array(text: str) -> list[dict]:
        match = re.search(r"\[.*\]", text, re.S)
        if not match:
            return []
        try:
            data = json.loads(match.group(0))
        except json.JSONDecodeError:
            return []
        return [e for e in data if isinstance(e, dict)]

    @staticmethod
    def _md_to_html(text: str) -> str:
        """极简 Markdown→HTML：## 标题、空行分段。够用即可，正文仍可在编辑器里调整。"""
        blocks = [b.strip() for b in re.split(r"\n\s*\n", text) if b.strip()]
        out: list[str] = []
        for b in blocks:
            heading = re.match(r"^(#{1,3})\s+(.*)$", b)
            if heading:
                level = len(heading.group(1)) + 1  # ## -> h3
                out.append(f"<h{level}>{html.escape(heading.group(2))}</h{level}>")
            else:
                out.append(f"<p>{html.escape(b)}</p>")
        return "".join(out)
