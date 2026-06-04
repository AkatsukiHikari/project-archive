"""
评测执行器（最小可用版）

设计稿 §7.4：黄金集驱动门禁，本期先实现"能跑通"的形态：
1. 拉某场景的所有黄金集条目
2. 逐条调被测能力（P1 只接 qa，其他场景占位返 "not_implemented"）
3. 比对 actual vs expected（按 rubric 类型走不同打分器）
4. 写 ai_eval_run / ai_eval_run_item，并把通过率写到 metrics
5. 若 settings.AI_EVAL_BLOCK_ON_REGRESSION=true 且未达 threshold → blocked_upgrade=true

调用方：管理员后台手动触发 / scripts/eval_run.py / CI 钩子。
"""
from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.modules.ai_eval.models.eval_run import EvalRun, EvalRunItem
from app.modules.ai_eval.models.golden_set import GoldenSetItem

logger = logging.getLogger(__name__)


# ── 打分器 ───────────────────────────────────────────────────────────────


def _score_qa(actual: dict[str, Any], expected: dict[str, Any]) -> tuple[bool, float, dict[str, Any]]:
    """问答场景打分（最简：关键词命中率 + 引用非空）。

    P1 只在乎"形态对了 + 有引用 + 期望关键词至少命中 1 个"，准确率打分留 P2 升级（embedding 相似度 / LLM 评判）。
    """
    answer = (actual.get("answer") or "").strip()
    citations = actual.get("citations") or []
    expected_keywords = expected.get("keywords") or []
    expected_refuse = bool(expected.get("refuse", False))

    diff: dict[str, Any] = {}

    if expected_refuse:
        # 期望拒答：答案为空或包含"无法回答"/"未查到"等关键字才算通过
        refuse_signal = any(
            kw in answer for kw in ("无法回答", "未查到", "无相关档案", "拒答")
        ) or not answer
        diff["expected_refuse"] = True
        diff["refuse_signal"] = refuse_signal
        return refuse_signal, 1.0 if refuse_signal else 0.0, diff

    if not answer:
        diff["reason"] = "answer empty"
        return False, 0.0, diff

    if not citations:
        diff["reason"] = "no citations"
        return False, 0.2, diff

    hits = [kw for kw in expected_keywords if kw and kw in answer]
    if expected_keywords and not hits:
        diff["reason"] = "no expected keyword hit"
        diff["expected_keywords"] = expected_keywords
        return False, 0.4, diff

    score = 1.0 if not expected_keywords else len(hits) / len(expected_keywords)
    diff["matched_keywords"] = hits
    return True, score, diff


_SCORERS = {
    "qa": _score_qa,
}


# ── 被测调用器 ─────────────────────────────────────────────────────────


async def _call_capability(
    scenario_code: str, payload: dict[str, Any]
) -> dict[str, Any]:
    """调被测能力（不走 HTTP，直接进 service 层）。

    P1：只接 qa；其他场景返回 "not_implemented"，runner 会把该条标记为跳过。
    """
    if scenario_code != "qa":
        return {"answer": "", "citations": [], "_skipped": True, "reason": "not_implemented"}

    # P1 演示：不真调 Dify（避免评测依赖外部服务跑通）。直接给个 mock 答案，
    # 让通路完整。P2 把这里改成 dify_service.stream_chat 全量消费。
    return {
        "answer": "（mock）" + (payload.get("query") or "")[:40],
        "citations": [],
        "_mock": True,
    }


# ── Runner ────────────────────────────────────────────────────────────


class EvalRunner:
    def __init__(self, db: AsyncSession):
        self._db = db

    async def run(
        self,
        *,
        tenant_id: uuid.UUID,
        scenario_code: str,
        workflow_version: str | None = None,
        model_tier: str | None = None,
        threshold: dict[str, float] | None = None,
    ) -> EvalRun:
        threshold = threshold or {"accuracy": 0.6}

        run = EvalRun(
            tenant_id=tenant_id,
            scenario_code=scenario_code,
            workflow_version=workflow_version,
            model_tier=model_tier,
            status="running",
            threshold=threshold,
            metrics={},
        )
        self._db.add(run)
        await self._db.flush()

        # 拉黄金集
        stmt = select(GoldenSetItem).where(
            GoldenSetItem.tenant_id == tenant_id,
            GoldenSetItem.scenario_code == scenario_code,
            GoldenSetItem.is_deleted.is_(False),
        )
        golden_rows = (await self._db.execute(stmt)).scalars().all()

        total = 0
        passed = 0
        skipped = 0
        score_sum = 0.0
        scorer = _SCORERS.get(scenario_code, _score_qa)

        for g in golden_rows:
            actual = await _call_capability(scenario_code, g.input or {})
            if actual.get("_skipped"):
                skipped += 1
                continue

            total += 1
            ok, score, diff = scorer(actual, g.expected or {})
            score_sum += score
            if ok:
                passed += 1

            self._db.add(
                EvalRunItem(
                    run_id=run.id,
                    golden_id=g.id,
                    actual=actual,
                    passed=ok,
                    score=score,
                    diff=diff,
                )
            )

        accuracy = (passed / total) if total else 0.0
        avg_score = (score_sum / total) if total else 0.0
        blocked = settings.AI_EVAL_BLOCK_ON_REGRESSION and accuracy < threshold.get(
            "accuracy", 0.0
        )

        run.status = "passed" if accuracy >= threshold.get("accuracy", 0.0) else "failed"
        run.total = total
        run.passed = passed
        run.metrics = {
            "accuracy": round(accuracy, 4),
            "avg_score": round(avg_score, 4),
            "skipped": skipped,
        }
        run.blocked_upgrade = blocked
        await self._db.flush()

        logger.info(
            "eval_run %s scenario=%s total=%d passed=%d acc=%.3f blocked=%s",
            run.id, scenario_code, total, passed, accuracy, blocked,
        )
        return run
