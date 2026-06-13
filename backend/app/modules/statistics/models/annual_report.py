"""档案事业统计年报（按《全国档案事业统计调查制度》DA-2 表口径）。

auto_data   系统自动计算的指标值（key → number），一键生成/重算
manual_data 人工填报的指标值（人员/馆库/设备/经费等系统无数据源的项）
状态机：draft（可重算可编辑）→ final（定稿锁定）
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.common.entity.base import BaseEntity


class StatAnnualReport(BaseEntity):
    __tablename__ = "stat_annual_report"

    year: Mapped[int] = mapped_column(
        Integer, nullable=False, index=True, comment="报告年度"
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="draft", comment="draft 草稿 | final 定稿"
    )
    auto_data: Mapped[Optional[dict]] = mapped_column(
        JSONB, nullable=True, comment="自动计算指标 key→value"
    )
    manual_data: Mapped[Optional[dict]] = mapped_column(
        JSONB, nullable=True, comment="人工填报指标 key→value"
    )
    generated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="最近一次自动计算时间"
    )
    finalized_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="定稿时间"
    )
    tenant_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("iam_tenant.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
