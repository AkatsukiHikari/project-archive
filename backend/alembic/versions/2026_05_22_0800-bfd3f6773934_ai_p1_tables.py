"""ai_p1_tables

P1 地基期新增 6 张 AI 模块表：
  - ai_scenario       AI 能力场景配置（按租户 × 能力码）
  - ai_session        用户会话索引
  - ai_patch          AI 写操作 staging（HITL 审核队列载体）
  - ai_golden_set     评测黄金集条目
  - ai_eval_run       评测执行总体记录
  - ai_eval_run_item  评测执行下样本结果
  - ai_annotation     待标注 / 已标注样本（驳回入池）

详见 docs/superpowers/specs/2026-05-11-archive-ai-agent-design.md §5.1。

Revision ID: bfd3f6773934
Revises: f9a3c81d2e45
Create Date: 2026-05-22 08:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "bfd3f6773934"
down_revision: Union[str, Sequence[str], None] = "f9a3c81d2e45"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── ai_scenario ─────────────────────────────────────────
    op.create_table(
        "ai_scenario",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, comment="唯一标识"),
        sa.Column(
            "create_time",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
            comment="创建时间",
        ),
        sa.Column(
            "update_time",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
            comment="更新时间",
        ),
        sa.Column("create_by", postgresql.UUID(as_uuid=True), nullable=True, comment="创建人ID"),
        sa.Column(
            "is_deleted",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
            comment="是否逻辑删除",
        ),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, comment="所属租户"),
        sa.Column(
            "scenario_code",
            sa.String(length=32),
            nullable=False,
            comment="能力码：qa/search/summary/attach/catalog/4nat/draft/relate/kb_manage",
        ),
        sa.Column("name", sa.String(length=64), nullable=False, comment="显示名称"),
        sa.Column("description", sa.Text(), nullable=True, comment="说明"),
        sa.Column(
            "enabled",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
            comment="是否启用",
        ),
        sa.Column("dify_app_id", sa.String(length=64), nullable=True, comment="对应 Dify App ID"),
        sa.Column(
            "dify_workflow_id", sa.String(length=64), nullable=True, comment="子 Workflow ID"
        ),
        sa.Column(
            "workflow_version",
            sa.String(length=32),
            nullable=True,
            comment="当前生效 Workflow 版本号",
        ),
        sa.Column(
            "default_model_tier",
            sa.String(length=8),
            server_default="准",
            nullable=False,
            comment="默认模型档位：快 / 准 / 思考",
        ),
        sa.Column(
            "model_mapping",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
            comment="档位→模型映射",
        ),
        sa.Column(
            "gate",
            sa.String(length=8),
            server_default="review",
            nullable=False,
            comment="HITL 闸门档位：auto / review / manual",
        ),
        sa.Column(
            "citation_required",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
            comment="是否强制引用",
        ),
        sa.Column(
            "extra_config",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
            comment="扩展配置",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["iam_tenant.id"], name="fk_ai_scenario_tenant", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_ai_scenario"),
        sa.UniqueConstraint("tenant_id", "scenario_code", name="uq_ai_scenario_tenant_code"),
    )
    op.create_index("ix_ai_scenario_tenant", "ai_scenario", ["tenant_id"], unique=False)

    # ── ai_session ──────────────────────────────────────────
    op.create_table(
        "ai_session",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, comment="唯一标识"),
        sa.Column(
            "create_time",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
            comment="创建时间",
        ),
        sa.Column(
            "update_time",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
            comment="更新时间",
        ),
        sa.Column("create_by", postgresql.UUID(as_uuid=True), nullable=True, comment="创建人ID"),
        sa.Column(
            "is_deleted",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
            comment="是否逻辑删除",
        ),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, comment="所属租户"),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False, comment="发起用户"),
        sa.Column(
            "dify_conversation_id",
            sa.String(length=64),
            nullable=True,
            comment="Dify 会话 ID",
        ),
        sa.Column(
            "title",
            sa.String(length=128),
            server_default="新对话",
            nullable=False,
            comment="会话标题",
        ),
        sa.Column(
            "last_scenario_code",
            sa.String(length=32),
            nullable=True,
            comment="上一次使用的场景",
        ),
        sa.Column(
            "last_model_tier", sa.String(length=8), nullable=True, comment="上一次使用的模型档位"
        ),
        sa.Column(
            "message_count",
            sa.Integer(),
            server_default="0",
            nullable=False,
            comment="消息数",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["iam_tenant.id"], name="fk_ai_session_tenant", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["iam_user.id"], name="fk_ai_session_user", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_ai_session"),
    )
    op.create_index(
        "ix_ai_session_user_recent",
        "ai_session",
        ["tenant_id", "user_id", "update_time"],
        unique=False,
    )
    op.create_index(
        "ix_ai_session_dify_conv", "ai_session", ["dify_conversation_id"], unique=False
    )

    # ── ai_patch ────────────────────────────────────────────
    op.create_table(
        "ai_patch",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, comment="唯一标识"),
        sa.Column(
            "create_time",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
            comment="创建时间",
        ),
        sa.Column(
            "update_time",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
            comment="更新时间",
        ),
        sa.Column("create_by", postgresql.UUID(as_uuid=True), nullable=True, comment="创建人ID"),
        sa.Column(
            "is_deleted",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
            comment="是否逻辑删除",
        ),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, comment="所属租户"),
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
            comment="提交时所在 AI 会话",
        ),
        sa.Column(
            "scenario_code", sa.String(length=32), nullable=False, comment="生成此 patch 的场景"
        ),
        sa.Column(
            "target_type", sa.String(length=32), nullable=False, comment="落库目标实体类型"
        ),
        sa.Column("target_id", postgresql.UUID(as_uuid=True), nullable=True, comment="目标 ID"),
        sa.Column("operation", sa.String(length=16), nullable=False, comment="create/update/delete"),
        sa.Column(
            "payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            comment="patch 数据",
        ),
        sa.Column(
            "payload_hash",
            sa.String(length=64),
            nullable=False,
            comment="payload SHA-256",
        ),
        sa.Column(
            "citations",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
            comment="引用列表",
        ),
        sa.Column("confidence", sa.Float(), nullable=True, comment="AI 置信度"),
        sa.Column(
            "gate",
            sa.String(length=8),
            server_default="review",
            nullable=False,
            comment="闸门档位",
        ),
        sa.Column(
            "status",
            sa.String(length=16),
            server_default="pending",
            nullable=False,
            comment="状态机",
        ),
        sa.Column(
            "reviewer_id", postgresql.UUID(as_uuid=True), nullable=True, comment="审核人 ID"
        ),
        sa.Column("reviewer_note", sa.Text(), nullable=True, comment="审核意见"),
        sa.Column(
            "workflow_version",
            sa.String(length=32),
            nullable=True,
            comment="产出该 patch 的 Workflow 版本",
        ),
        sa.Column(
            "dify_message_id",
            sa.String(length=64),
            nullable=True,
            comment="关联 Dify message_id",
        ),
        sa.Column("apply_error", sa.Text(), nullable=True, comment="落库失败错误信息"),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["iam_tenant.id"], name="fk_ai_patch_tenant", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["session_id"], ["ai_session.id"], name="fk_ai_patch_session", ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["reviewer_id"], ["iam_user.id"], name="fk_ai_patch_reviewer", ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_ai_patch"),
    )
    op.create_index("ix_ai_patch_tenant_status", "ai_patch", ["tenant_id", "status"], unique=False)
    op.create_index("ix_ai_patch_scenario", "ai_patch", ["scenario_code"], unique=False)
    op.create_index("ix_ai_patch_target", "ai_patch", ["target_type", "target_id"], unique=False)
    op.create_index("ix_ai_patch_session", "ai_patch", ["session_id"], unique=False)

    # ── ai_golden_set ───────────────────────────────────────
    op.create_table(
        "ai_golden_set",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, comment="唯一标识"),
        sa.Column(
            "create_time",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
            comment="创建时间",
        ),
        sa.Column(
            "update_time",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
            comment="更新时间",
        ),
        sa.Column("create_by", postgresql.UUID(as_uuid=True), nullable=True, comment="创建人ID"),
        sa.Column(
            "is_deleted",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
            comment="是否逻辑删除",
        ),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            comment="所属租户（黄金集按租户隔离）",
        ),
        sa.Column("scenario_code", sa.String(length=32), nullable=False, comment="所属能力"),
        sa.Column(
            "input", postgresql.JSONB(astext_type=sa.Text()), nullable=False, comment="输入"
        ),
        sa.Column(
            "expected",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            comment="期望输出 / 评分 rubric",
        ),
        sa.Column(
            "tags",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
            comment="标签",
        ),
        sa.Column(
            "source",
            sa.String(length=16),
            server_default="seed",
            nullable=False,
            comment="来源",
        ),
        sa.Column("note", sa.Text(), nullable=True, comment="备注"),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["iam_tenant.id"], name="fk_ai_golden_tenant", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_ai_golden_set"),
    )
    op.create_index(
        "ix_ai_golden_tenant_scenario",
        "ai_golden_set",
        ["tenant_id", "scenario_code"],
        unique=False,
    )
    op.create_index("ix_ai_golden_source", "ai_golden_set", ["source"], unique=False)

    # ── ai_eval_run ─────────────────────────────────────────
    op.create_table(
        "ai_eval_run",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, comment="唯一标识"),
        sa.Column(
            "create_time",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
            comment="创建时间",
        ),
        sa.Column(
            "update_time",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
            comment="更新时间",
        ),
        sa.Column("create_by", postgresql.UUID(as_uuid=True), nullable=True, comment="创建人ID"),
        sa.Column(
            "is_deleted",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
            comment="是否逻辑删除",
        ),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("scenario_code", sa.String(length=32), nullable=False),
        sa.Column(
            "workflow_version",
            sa.String(length=32),
            nullable=True,
            comment="被评测的 Workflow 版本",
        ),
        sa.Column(
            "model_tier", sa.String(length=8), nullable=True, comment="被评测的模型档位"
        ),
        sa.Column(
            "status",
            sa.String(length=16),
            server_default="pending",
            nullable=False,
            comment="状态机",
        ),
        sa.Column("total", sa.Integer(), nullable=True, comment="样本总数"),
        sa.Column("passed", sa.Integer(), nullable=True, comment="通过数"),
        sa.Column(
            "metrics",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
            comment="指标快照",
        ),
        sa.Column(
            "threshold",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
            comment="本次门禁阈值",
        ),
        sa.Column(
            "blocked_upgrade",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
            comment="是否因不达标而阻断上线",
        ),
        sa.Column("error_message", sa.Text(), nullable=True, comment="评测过程错误信息"),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["iam_tenant.id"], name="fk_ai_eval_run_tenant", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_ai_eval_run"),
    )
    op.create_index(
        "ix_ai_eval_run_tenant_scenario",
        "ai_eval_run",
        ["tenant_id", "scenario_code"],
        unique=False,
    )
    op.create_index("ix_ai_eval_run_status", "ai_eval_run", ["status"], unique=False)

    # ── ai_eval_run_item ───────────────────────────────────
    op.create_table(
        "ai_eval_run_item",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, comment="唯一标识"),
        sa.Column(
            "create_time",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
            comment="创建时间",
        ),
        sa.Column(
            "update_time",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
            comment="更新时间",
        ),
        sa.Column("create_by", postgresql.UUID(as_uuid=True), nullable=True, comment="创建人ID"),
        sa.Column(
            "is_deleted",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
            comment="是否逻辑删除",
        ),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("golden_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "actual",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            comment="实际输出",
        ),
        sa.Column(
            "passed",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("score", sa.Float(), nullable=True, comment="评分（0~1）"),
        sa.Column(
            "diff",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
            comment="与期望的 diff",
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["run_id"], ["ai_eval_run.id"], name="fk_ai_eval_item_run", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["golden_id"], ["ai_golden_set.id"], name="fk_ai_eval_item_golden", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_ai_eval_run_item"),
    )
    op.create_index("ix_ai_eval_item_run", "ai_eval_run_item", ["run_id"], unique=False)
    op.create_index(
        "ix_ai_eval_item_passed", "ai_eval_run_item", ["run_id", "passed"], unique=False
    )

    # ── ai_annotation ──────────────────────────────────────
    op.create_table(
        "ai_annotation",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, comment="唯一标识"),
        sa.Column(
            "create_time",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
            comment="创建时间",
        ),
        sa.Column(
            "update_time",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
            comment="更新时间",
        ),
        sa.Column("create_by", postgresql.UUID(as_uuid=True), nullable=True, comment="创建人ID"),
        sa.Column(
            "is_deleted",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
            comment="是否逻辑删除",
        ),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("scenario_code", sa.String(length=32), nullable=False),
        sa.Column(
            "source",
            sa.String(length=16),
            server_default="reject_pool",
            nullable=False,
            comment="来源",
        ),
        sa.Column(
            "patch_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
            comment="来源 patch（若由驳回入池）",
        ),
        sa.Column(
            "input",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            comment="输入快照",
        ),
        sa.Column(
            "ai_output",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            comment="AI 当时的输出",
        ),
        sa.Column(
            "expected",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="标注后的期望输出",
        ),
        sa.Column(
            "status",
            sa.String(length=16),
            server_default="pending",
            nullable=False,
            comment="状态",
        ),
        sa.Column(
            "annotator_id", postgresql.UUID(as_uuid=True), nullable=True, comment="标注人 ID"
        ),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column(
            "promoted_golden_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
            comment="若已转入黄金集，对应的 golden_id",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["iam_tenant.id"], name="fk_ai_annot_tenant", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["patch_id"], ["ai_patch.id"], name="fk_ai_annot_patch", ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["annotator_id"],
            ["iam_user.id"],
            name="fk_ai_annot_annotator",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["promoted_golden_id"],
            ["ai_golden_set.id"],
            name="fk_ai_annot_golden",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_ai_annotation"),
    )
    op.create_index(
        "ix_ai_annotation_tenant_status",
        "ai_annotation",
        ["tenant_id", "status"],
        unique=False,
    )
    op.create_index("ix_ai_annotation_scenario", "ai_annotation", ["scenario_code"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_ai_annotation_scenario", table_name="ai_annotation")
    op.drop_index("ix_ai_annotation_tenant_status", table_name="ai_annotation")
    op.drop_table("ai_annotation")
    op.drop_index("ix_ai_eval_item_passed", table_name="ai_eval_run_item")
    op.drop_index("ix_ai_eval_item_run", table_name="ai_eval_run_item")
    op.drop_table("ai_eval_run_item")
    op.drop_index("ix_ai_eval_run_status", table_name="ai_eval_run")
    op.drop_index("ix_ai_eval_run_tenant_scenario", table_name="ai_eval_run")
    op.drop_table("ai_eval_run")
    op.drop_index("ix_ai_golden_source", table_name="ai_golden_set")
    op.drop_index("ix_ai_golden_tenant_scenario", table_name="ai_golden_set")
    op.drop_table("ai_golden_set")
    op.drop_index("ix_ai_patch_session", table_name="ai_patch")
    op.drop_index("ix_ai_patch_target", table_name="ai_patch")
    op.drop_index("ix_ai_patch_scenario", table_name="ai_patch")
    op.drop_index("ix_ai_patch_tenant_status", table_name="ai_patch")
    op.drop_table("ai_patch")
    op.drop_index("ix_ai_session_dify_conv", table_name="ai_session")
    op.drop_index("ix_ai_session_user_recent", table_name="ai_session")
    op.drop_table("ai_session")
    op.drop_index("ix_ai_scenario_tenant", table_name="ai_scenario")
    op.drop_table("ai_scenario")
