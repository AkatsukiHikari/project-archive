"""drop legacy AI agent tables (agents/eval/patch/session/scenario)

AI 重构：删除旧的多 agent / 评测 / 写库 HITL / 会话 / 场景 体系。
保留 dify_service；新体系围绕 OCR 工作流 + Dify 知识库 + ES 检索问答。

Revision ID: d6e7f8a9b0c1
Revises: c5d6e7f8a9b0
Create Date: 2026-06-21 09:00
"""

from typing import Sequence, Union

from alembic import op

revision: str = "d6e7f8a9b0c1"
down_revision: Union[str, Sequence[str], None] = "c5d6e7f8a9b0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TABLES = [
    "ai_eval_run_item",
    "ai_eval_run",
    "ai_golden_set",
    "ai_annotation",
    "ai_patch",
    "ai_session",
    "ai_scenario",
]


def upgrade() -> None:
    for t in _TABLES:
        op.execute(f'DROP TABLE IF EXISTS "{t}" CASCADE')


def downgrade() -> None:
    # 旧体系已废弃，不提供回滚重建
    pass
