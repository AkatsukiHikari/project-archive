"""AI 预鉴定引擎。

两阶段，结果只写 appr_item 的 AI 建议字段，绝不直接修改档案：
  ① 确定性规则（同步、必跑）：密级未解除 / 敏感词命中 / 标准条款关键词命中
  ② LLM 语义补判（后台、可选）：对规则判为"开放"的条目让大模型复核语义敏感性；
     未配置 Dify key 时自动跳过。

结论严重度：不开放 > 延期开放 > 控制使用 > 开放。
"""

import asyncio
import json
import logging
import re
import uuid
from typing import Optional

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.infra.db.session import AsyncSessionLocal
from app.modules.ai.services.dify_service import dify_service
from app.modules.appraisal.models import (AppraisalItem,
                                          AppraisalSensitiveWord,
                                          AppraisalStandard, AppraisalTask)
from app.modules.repository.models.archive import Archive

logger = logging.getLogger(__name__)

SEVERITY = {"开放": 0, "控制使用": 1, "延期开放": 2, "不开放": 3}
PUBLIC_MJ_VALUES = ("无", "", "公开", "public")  # 无密级即可开放（兼容历史值）
LLM_CHUNK_SIZE = 20


class AiAppraisalEngine:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ── 入口：启动任务级预鉴定 ────────────────────────────────────────────────

    async def start(self, task: AppraisalTask, user_id: uuid.UUID) -> None:
        """同步跑规则阶段并置 ai_running。调用方 commit 后再 spawn_llm_stage。"""
        standards, words = await self._load_rules(task.tenant_id)
        items = await self._load_items(task.id)
        archives = await self._load_archives(items)

        for item in items:
            if item.status == "decided":
                continue
            self._rule_suggest(item, archives.get(item.archive_id), standards, words)

        task.status = "ai_running"
        await self.db.flush()

    @staticmethod
    def spawn_llm_stage(task_id: uuid.UUID, user_id: uuid.UUID) -> None:
        """启动 LLM 语义复核后台任务。必须在规则阶段 commit 之后调用，
        否则后台会话读不到刚写入的 AI 建议。"""
        asyncio.create_task(
            _llm_stage_background(task_id, str(user_id)),
            name=f"appraisal-llm-{task_id}",
        )

    # ── 阶段①：确定性规则 ────────────────────────────────────────────────────

    def _rule_suggest(
        self,
        item: AppraisalItem,
        archive: Optional[Archive],
        standards: list[AppraisalStandard],
        words: list[AppraisalSensitiveWord],
    ) -> None:
        text = self._scan_text(item, archive)

        # 密级未解除 → 控制使用
        if item.MJ and item.MJ not in PUBLIC_MJ_VALUES:
            self._apply(
                item,
                "控制使用",
                f"密级为「{item.MJ}」，未经解密不予开放",
                None,
                None,
                1.0,
            )

        # 敏感词命中
        hits = [w for w in words if w.word in text]
        if hits:
            worst = max(hits, key=lambda w: SEVERITY.get(w.suggest_kfzt, 1))
            hit_words = [w.word for w in hits]
            reason = f"命中敏感词：{('、'.join(hit_words))}（{worst.category or '敏感内容'}）"
            self._apply(item, worst.suggest_kfzt, reason, None, hit_words, 1.0)

        # 标准条款关键词命中
        for std in standards:
            if not std.keywords:
                continue
            matched = [k for k in std.keywords if k and k in text]
            if matched:
                reason = f"依据{std.source or std.title}（{std.code}）：{std.content}"
                self._apply(item, std.target_kfzt, reason, std.code, None, 0.9)

        # 无任何命中 → 建议开放（引用开放导向的标准条款）
        if item.ai_kfzt is None:
            open_std = next((s for s in standards if s.target_kfzt == "开放"), None)
            if open_std:
                reason = (
                    f"{item.due_basis or '保管期限届满'}，未涉及控制范围；"
                    f"依据{open_std.source or open_std.title}（{open_std.code}）建议开放"
                )
                self._apply(item, "开放", reason, open_std.code, None, 0.8)
            else:
                self._apply(
                    item,
                    "开放",
                    f"{item.due_basis or '保管期限届满'}，未命中任何控制条款，建议开放",
                    None,
                    None,
                    0.7,
                )

        item.ai_status = "done"

    @staticmethod
    def _apply(
        item: AppraisalItem,
        kfzt: str,
        reason: str,
        standard_code: Optional[str],
        hit_words: Optional[list[str]],
        confidence: float,
    ) -> None:
        """只允许结论升级（更严），不允许降级覆盖。"""
        if item.ai_kfzt is not None and SEVERITY.get(kfzt, 0) <= SEVERITY.get(
            item.ai_kfzt, 0
        ):
            return
        item.ai_kfzt = kfzt
        item.ai_reason = reason
        item.ai_standard_code = standard_code
        if hit_words:
            item.ai_hit_words = hit_words
        item.ai_confidence = confidence

    @staticmethod
    def _scan_text(item: AppraisalItem, archive: Optional[Archive]) -> str:
        parts = [item.TM or "", item.DH or ""]
        if archive:
            parts.append(archive.RZZ or "")
            if archive.ext_fields:
                parts.extend(str(v) for v in archive.ext_fields.values() if v)
        return " ".join(parts)

    # ── 数据加载 ──────────────────────────────────────────────────────────────

    async def _load_rules(
        self, tenant_id: Optional[uuid.UUID]
    ) -> tuple[list[AppraisalStandard], list[AppraisalSensitiveWord]]:
        std_stmt = (
            select(AppraisalStandard)
            .where(
                AppraisalStandard.is_deleted.is_(False),
                AppraisalStandard.is_enabled.is_(True),
            )
            .order_by(AppraisalStandard.sort_order)
        )
        word_stmt = select(AppraisalSensitiveWord).where(
            AppraisalSensitiveWord.is_deleted.is_(False),
            AppraisalSensitiveWord.is_enabled.is_(True),
        )
        if tenant_id:
            std_stmt = std_stmt.where(
                or_(
                    AppraisalStandard.tenant_id == tenant_id,
                    AppraisalStandard.tenant_id.is_(None),
                )
            )
            word_stmt = word_stmt.where(
                or_(
                    AppraisalSensitiveWord.tenant_id == tenant_id,
                    AppraisalSensitiveWord.tenant_id.is_(None),
                )
            )
        standards = (await self.db.execute(std_stmt)).scalars().all()
        words = (await self.db.execute(word_stmt)).scalars().all()
        return list(standards), list(words)

    async def _load_items(self, task_id: uuid.UUID) -> list[AppraisalItem]:
        return list(
            (
                await self.db.execute(
                    select(AppraisalItem).where(
                        AppraisalItem.task_id == task_id,
                        AppraisalItem.is_deleted.is_(False),
                    )
                )
            ).scalars()
        )

    async def _load_archives(
        self, items: list[AppraisalItem]
    ) -> dict[uuid.UUID, Archive]:
        ids = [i.archive_id for i in items]
        if not ids:
            return {}
        archives = (
            (await self.db.execute(select(Archive).where(Archive.id.in_(ids))))
            .scalars()
            .all()
        )
        return {a.id: a for a in archives}


# ── 阶段②：LLM 语义补判（后台任务，独立 session）────────────────────────────


async def _llm_stage_background(task_id: uuid.UUID, user_id: str) -> None:
    try:
        async with AsyncSessionLocal() as db:
            await _llm_stage(db, task_id, user_id)
            await db.commit()
    except Exception:
        logger.exception("AI 预鉴定 LLM 阶段失败 task=%s", task_id)
        try:
            async with AsyncSessionLocal() as db:
                await _finish_task(db, task_id)
                await db.commit()
        except Exception:
            logger.exception("AI 预鉴定收尾失败 task=%s", task_id)


async def _llm_stage(db: AsyncSession, task_id: uuid.UUID, user_id: str) -> None:
    api_key = settings.dify_api_key_for("appraisal")
    items = list(
        (
            await db.execute(
                select(AppraisalItem).where(
                    AppraisalItem.task_id == task_id,
                    AppraisalItem.is_deleted.is_(False),
                    AppraisalItem.status == "pending",
                    AppraisalItem.ai_kfzt == "开放",
                )
            )
        ).scalars()
    )

    if api_key and items:
        standards = list(
            (
                await db.execute(
                    select(AppraisalStandard).where(
                        AppraisalStandard.is_deleted.is_(False),
                        AppraisalStandard.is_enabled.is_(True),
                    )
                )
            ).scalars()
        )
        for start in range(0, len(items), LLM_CHUNK_SIZE):
            chunk = items[start : start + LLM_CHUNK_SIZE]
            try:
                await _llm_review_chunk(chunk, standards, user_id, api_key)
            except Exception:
                logger.exception("LLM 复核分片失败 task=%s offset=%d", task_id, start)
            await db.flush()

    await _finish_task(db, task_id)


async def _finish_task(db: AsyncSession, task_id: uuid.UUID) -> None:
    task = (
        (await db.execute(select(AppraisalTask).where(AppraisalTask.id == task_id)))
        .scalars()
        .first()
    )
    if task and task.status == "ai_running":
        task.status = "ai_done"


async def _llm_review_chunk(
    items: list[AppraisalItem],
    standards: list[AppraisalStandard],
    user_id: str,
    api_key: str,
) -> None:
    """让 LLM 复核一批规则判为「开放」的条目，发现语义敏感即升级结论。"""
    std_text = "\n".join(
        f"- {s.code}（导向{s.target_kfzt}）：{s.content}" for s in standards
    )
    item_text = "\n".join(
        f"{idx}. 题名：{i.TM}｜档号：{i.DH or '无'}｜年度：{i.ND or '无'}"
        for idx, i in enumerate(items)
    )
    query = (
        "你是档案开放鉴定专家。以下档案经规则初判为「开放」，请逐条复核题名语义，"
        "判断是否涉及国家安全、国防、外交、个人隐私、商业秘密等不宜开放的内容。\n"
        f"鉴定标准条款：\n{std_text}\n\n待复核档案：\n{item_text}\n\n"
        "只输出 JSON 数组，不要其他文字。每个元素格式："
        '{"idx": 序号, "kfzt": "开放|控制使用|延期开放|不开放", '
        '"reason": "结论理由", "standard_code": "引用条款编码或null", "confidence": 0到1}'
    )

    answer = await _collect_answer(query, user_id, api_key)
    if not answer:
        return

    for entry in _parse_json_array(answer):
        idx = entry.get("idx")
        kfzt = entry.get("kfzt")
        if not isinstance(idx, int) or idx >= len(items) or kfzt not in SEVERITY:
            continue
        item = items[idx]
        # LLM 只允许把「开放」升级为更严的结论
        if SEVERITY[kfzt] <= SEVERITY.get(item.ai_kfzt or "开放", 0):
            continue
        item.ai_kfzt = kfzt
        item.ai_reason = f"AI 语义复核：{entry.get('reason') or '内容涉敏'}"
        item.ai_standard_code = entry.get("standard_code") or item.ai_standard_code
        try:
            item.ai_confidence = float(entry.get("confidence") or 0.6)
        except (TypeError, ValueError):
            item.ai_confidence = 0.6


async def _collect_answer(query: str, user_id: str, api_key: str) -> str:
    """消费 Dify SSE 流，拼出完整回答文本。"""
    answer_parts: list[str] = []
    async for line in dify_service.stream_chat(
        query=query, user_id=user_id, scenario_code="appraisal", api_key=api_key
    ):
        line = line.strip()
        if not line.startswith("data:"):
            continue
        try:
            event = json.loads(line[5:].strip())
        except json.JSONDecodeError:
            continue
        if event.get("event") == "error":
            logger.warning("Dify 返回错误: %s", event.get("message"))
            return ""
        if event.get("event") in ("message", "agent_message"):
            answer_parts.append(event.get("answer") or "")
    return "".join(answer_parts)


def _parse_json_array(text: str) -> list[dict]:
    """从 LLM 回答中提取 JSON 数组（容忍 ```json 包裹等噪声）。"""
    match = re.search(r"\[.*\]", text, re.S)
    if not match:
        return []
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return []
    return [e for e in data if isinstance(e, dict)]
