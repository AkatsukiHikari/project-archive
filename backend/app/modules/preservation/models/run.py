"""四性检测：检测记录 + 结果明细 模型。"""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Integer, Float, Boolean, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.common.entity.base import BaseEntity


class DetectionBatch(BaseEntity):
    """一个检测批次（每次点"检测"=一个全新批次，含 1~N 件的检测）。"""
    __tablename__ = "pres_batch"

    batch_no: Mapped[str] = mapped_column(String(40), nullable=False, index=True, comment="批次号 SXyyyymmddNNN")
    scope_type: Mapped[str] = mapped_column(String(20), nullable=False, default="single", comment="single | fonds | catalog | category | year | mixed")
    scope_label: Mapped[Optional[str]] = mapped_column(String(512), nullable=True, comment="检测范围描述")
    scheme_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("pres_scheme.id", ondelete="SET NULL"), nullable=True
    )
    scheme_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    total: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="件数")
    passed: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="合格件数")
    warned: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="基本合格件数")
    failed: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="不合格件数")
    pending: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="待复核件数")
    avg_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, comment="平均分")
    dim_scores: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True, comment="批次各维度平均分")
    conclusion: Mapped[str] = mapped_column(String(20), nullable=False, default="pass", comment="pass 全部合格 | warn | fail 含不合格 | pending 含待复核")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="done")
    operator_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("iam_user.id", ondelete="SET NULL"), nullable=True
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    report_key: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    tenant_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("iam_tenant.id", ondelete="CASCADE"), nullable=True, index=True
    )


class DetectionRun(BaseEntity):
    """一次四性检测运行（批次内单件的检测）。"""
    __tablename__ = "pres_run"

    batch_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("pres_batch.id", ondelete="CASCADE"), nullable=True, index=True
    )
    target_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="archive", comment="对象类型: archive | batch | file"
    )
    target_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True, comment="对象ID（无DB FK）")
    target_label: Mapped[Optional[str]] = mapped_column(String(512), nullable=True, comment="对象题名/档号快照")
    scheme_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("pres_scheme.id", ondelete="SET NULL"), nullable=True
    )
    scheme_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True, comment="方案名快照")
    scheme_version: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    overall_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, comment="总分(0-100)")
    dim_scores: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True, comment="各维度得分")
    conclusion: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending",
        comment="结论: pass 合格 | warn 基本合格 | fail 不合格 | pending 待复核",
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="done", comment="running | done | failed")
    total: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="检测项数")
    passed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    warned: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    manual_pending: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="待人工核验项数")

    operator_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("iam_user.id", ondelete="SET NULL"), nullable=True, comment="检测人"
    )
    reviewer_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("iam_user.id", ondelete="SET NULL"), nullable=True, comment="复核人"
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    report_key: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True, comment="检测报告对象键")
    tenant_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("iam_tenant.id", ondelete="CASCADE"), nullable=True, index=True
    )


class DetectionResultItem(BaseEntity):
    """检测结果明细（逐项)。"""
    __tablename__ = "pres_run_result"

    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("pres_run.id", ondelete="CASCADE"), nullable=False, index=True
    )
    check_code: Mapped[str] = mapped_column(String(64), nullable=False)
    check_name: Mapped[str] = mapped_column(String(200), nullable=False)
    dimension: Mapped[str] = mapped_column(String(20), nullable=False)
    exec_type: Mapped[str] = mapped_column(String(10), nullable=False)
    result: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pass",
        comment="pass | warn | fail | skip | manual_pending",
    )
    score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    weight: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    is_blocking: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    message: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="结论/问题/整改建议")
    evidence: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True, comment="证据/明细")
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True, comment="AI 判定置信度")
    standard_ref: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    decided_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("iam_user.id", ondelete="SET NULL"), nullable=True, comment="人工判定/覆盖人"
    )
    tenant_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("iam_tenant.id", ondelete="CASCADE"), nullable=True, index=True
    )
