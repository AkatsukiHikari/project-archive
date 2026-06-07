import uuid
from datetime import date, datetime
from typing import Optional

from sqlalchemy import String, Integer, Float, Boolean, Date, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.common.entity.base import BaseEntity


class TransferBatch(BaseEntity):
    """
    移交单（移交清单）。

    一个移交单位的一批档案移交，状态机：
      draft → submitted（移交单位提交）
            → received（档案室签收、四性预检）
            → accepted（接收通过，明细转入暂存库 pending_review）
            → returned（退回，附退回原因）
    """
    __tablename__ = "col_transfer_batch"

    transfer_no: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True, comment="移交单号（自动生成）"
    )
    plan_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("col_transfer_plan.id", ondelete="SET NULL"),
        nullable=True, index=True, comment="关联归档计划"
    )
    source_unit: Mapped[str] = mapped_column(
        String(200), nullable=False, index=True, comment="移交单位名称"
    )
    source_org_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True, comment="移交单位组织ID（无 DB FK 约束）"
    )
    fonds_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("repo_fonds.id", ondelete="RESTRICT"),
        nullable=False, index=True, comment="目标全宗"
    )
    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("repo_archive_category.id", ondelete="RESTRICT"),
        nullable=False, index=True, comment="档案门类"
    )
    catalog_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("repo_catalog.id", ondelete="RESTRICT"),
        nullable=True, index=True, comment="目标目录（接收时确定）"
    )
    year: Mapped[int] = mapped_column(
        Integer, nullable=False, index=True, comment="移交档案年度"
    )
    handover_person: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="移交经办人"
    )
    handover_date: Mapped[Optional[date]] = mapped_column(
        Date, nullable=True, comment="移交日期"
    )
    expected_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="申报移交件数"
    )

    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="draft", index=True,
        comment="状态: draft | submitted | received | accepted | returned",
    )
    submitted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="提交移交时间"
    )
    received_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="签收时间"
    )
    accepted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="接收通过时间"
    )
    handler_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("iam_user.id", ondelete="SET NULL"),
        nullable=True, comment="接收经办人（档案室）"
    )

    # 四性预检闸门结果
    precheck_score: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True, comment="四性预检总分(0-100)"
    )
    precheck_passed: Mapped[Optional[bool]] = mapped_column(
        Boolean, nullable=True, comment="四性预检是否通过闸门阈值"
    )
    precheck_detail: Mapped[Optional[dict]] = mapped_column(
        JSONB, nullable=True, comment="四性预检明细（真实/完整/可用/安全维度）"
    )

    return_reason: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="退回原因"
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="备注")
    tenant_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("iam_tenant.id", ondelete="CASCADE"),
        nullable=True, index=True
    )


class TransferEntry(BaseEntity):
    """
    移交明细（移交清单内的单条档案条目，DA/T 拼音缩写字段）。

    接收通过后，每条明细物化为 repo_archive_staging 记录（pending_review），
    staging_id 回填，复用既有著录/审核/入正式库流水线。
    """
    __tablename__ = "col_transfer_entry"

    batch_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("col_transfer_batch.id", ondelete="CASCADE"),
        nullable=False, index=True, comment="所属移交单"
    )
    row_no: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="清单内序号"
    )

    TM: Mapped[str] = mapped_column(String(512), nullable=False, comment="题名")
    RZZ: Mapped[Optional[str]] = mapped_column(String(200), nullable=True, comment="责任者")
    ND: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="年度")
    WJRQ: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, comment="文件日期")
    YS: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="页数")
    MJ: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, comment="密级")
    BGQX: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, comment="保管期限")
    ext_fields: Mapped[Optional[dict]] = mapped_column(
        JSONB, nullable=True, comment="门类私有字段"
    )

    precheck_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending",
        comment="单条预检状态: pending | ok | warning | error",
    )
    precheck_issues: Mapped[Optional[dict]] = mapped_column(
        JSONB, nullable=True, comment="单条预检问题列表"
    )
    staging_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True,
        comment="接收后物化的暂存库记录 ID（无 DB FK 约束）"
    )
    tenant_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("iam_tenant.id", ondelete="CASCADE"),
        nullable=True, index=True
    )
