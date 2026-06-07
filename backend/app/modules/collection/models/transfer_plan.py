import uuid
from datetime import date
from typing import Optional

from sqlalchemy import String, Integer, Date, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.common.entity.base import BaseEntity


class TransferPlan(BaseEntity):
    """
    归档计划（应交计划）。

    按年度为各移交单位下达"应交档案"任务，是收集台账"催交看板"的依据：
    应交件数 vs 已接收件数 → 完成率 / 欠交 / 逾期。
    """
    __tablename__ = "col_transfer_plan"

    year: Mapped[int] = mapped_column(
        Integer, nullable=False, index=True, comment="计划年度"
    )
    source_unit: Mapped[str] = mapped_column(
        String(200), nullable=False, index=True, comment="移交单位名称"
    )
    source_org_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True,
        comment="移交单位组织ID（无 DB FK 约束）"
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
    planned_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="应交件数"
    )
    due_date: Mapped[Optional[date]] = mapped_column(
        Date, nullable=True, comment="应交截止日期"
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="active",
        comment="计划状态: active | closed",
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="备注")
    tenant_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("iam_tenant.id", ondelete="CASCADE"),
        nullable=True, index=True
    )
