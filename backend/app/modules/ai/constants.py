"""
AI 模块常量

集中存放跨服务/路由复用的字面量，避免散落各处魔法字符串。
"""

from typing import Final

# ── 审计动作码（写入 audit_log.action 列） ────────────────────────────
# 见设计稿 §7.3：所有 AI 动作审计都带 scenario_code / model_tier / workflow_version / dify_message_id
AUDIT_AI_CHAT_QUERY: Final[str] = "ai_chat_query"
AUDIT_AI_TOOL_CALL: Final[str] = "ai_tool_call"
AUDIT_AI_PATCH_CREATE: Final[str] = "ai_patch_create"
AUDIT_AI_PATCH_APPROVE: Final[str] = "ai_patch_approve"
AUDIT_AI_PATCH_REJECT: Final[str] = "ai_patch_reject"
AUDIT_AI_EVAL_RUN: Final[str] = "ai_eval_run"

ALL_AI_AUDIT_ACTIONS: Final[tuple[str, ...]] = (
    AUDIT_AI_CHAT_QUERY,
    AUDIT_AI_TOOL_CALL,
    AUDIT_AI_PATCH_CREATE,
    AUDIT_AI_PATCH_APPROVE,
    AUDIT_AI_PATCH_REJECT,
    AUDIT_AI_EVAL_RUN,
)


# ── Patch 状态机 ───────────────────────────────────────────────────────
PATCH_STATUS_PENDING: Final[str] = "pending"
PATCH_STATUS_APPROVED: Final[str] = "approved"
PATCH_STATUS_REJECTED: Final[str] = "rejected"
PATCH_STATUS_APPLIED: Final[str] = "applied"
PATCH_STATUS_FAILED: Final[str] = "failed"

VALID_PATCH_STATUSES: Final[frozenset[str]] = frozenset(
    {
        PATCH_STATUS_PENDING,
        PATCH_STATUS_APPROVED,
        PATCH_STATUS_REJECTED,
        PATCH_STATUS_APPLIED,
        PATCH_STATUS_FAILED,
    }
)


# ── HITL 闸门档位 ──────────────────────────────────────────────────────
GATE_AUTO: Final[str] = "auto"
GATE_REVIEW: Final[str] = "review"
GATE_MANUAL: Final[str] = "manual"

VALID_GATES: Final[frozenset[str]] = frozenset({GATE_AUTO, GATE_REVIEW, GATE_MANUAL})


# ── 评测状态机 ─────────────────────────────────────────────────────────
EVAL_STATUS_PENDING: Final[str] = "pending"
EVAL_STATUS_RUNNING: Final[str] = "running"
EVAL_STATUS_PASSED: Final[str] = "passed"
EVAL_STATUS_FAILED: Final[str] = "failed"
EVAL_STATUS_ERROR: Final[str] = "error"


# ── 引用来源类型（出现在 ai_patch.citations[].source_type） ────────────
CITATION_SOURCE_META: Final[str] = "meta"
CITATION_SOURCE_RULE: Final[str] = "rule"
CITATION_SOURCE_OCR: Final[str] = "ocr"
