import uuid
from datetime import datetime, date
from typing import Optional

from sqlalchemy import String, Integer, Numeric, Text, Date, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.common.entity.base import BaseEntity


class UtilizationApplication(BaseEntity):
    """
    利用申请 / 利用登记（一个来馆查档的人 = 一条登记）。

    流程：办理中(processing) → 办理完成(completed) / 已取消(cancelled)。
    办结后，其调阅篮(util_item)即沉淀为利用登记明细，供"利用台账"统计。
    """
    __tablename__ = "util_application"

    reg_no: Mapped[str] = mapped_column(
        String(40), nullable=False, index=True, comment="利用登记流水号 LYyyyymmddNNN"
    )
    applicant_name: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True, comment="利用人姓名"
    )
    id_card_no: Mapped[Optional[str]] = mapped_column(
        String(32), nullable=True, index=True, comment="身份证号（读卡或手填）"
    )
    gender: Mapped[Optional[str]] = mapped_column(String(8), nullable=True, comment="性别")
    phone: Mapped[Optional[str]] = mapped_column(String(32), nullable=True, comment="联系电话")
    organization: Mapped[Optional[str]] = mapped_column(
        String(200), nullable=True, comment="工作单位"
    )
    avatar_key: Mapped[Optional[str]] = mapped_column(
        String(1024), nullable=True, comment="身份证头像对象键（无则前端用姓氏首字）"
    )
    purpose: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="利用目的")
    use_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="read",
        comment="利用方式: read 查阅 | borrow 借阅 | copy 复制 | certificate 证明",
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="processing", index=True,
        comment="状态: pending 待审批(自助机) | processing 办理中 | completed 办理完成 | cancelled 已取消 | rejected 已拒绝",
    )
    handler_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("iam_user.id", ondelete="SET NULL"),
        nullable=True, comment="经办人（档案馆窗口）"
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="办结时间"
    )

    # ── 自助查询机（kiosk）通道 ──
    source: Mapped[str] = mapped_column(
        String(10), nullable=False, default="counter",
        comment="来源: counter 柜台 | kiosk 自助查询机",
    )
    access_code: Mapped[Optional[str]] = mapped_column(
        String(8), nullable=True, index=True,
        comment="自助机申请码（民众凭码取回/阅览，办结后失效）",
    )
    approved_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("iam_user.id", ondelete="SET NULL"),
        nullable=True, comment="审批人（自助机申请）",
    )
    approved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="审批时间"
    )
    reject_reason: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True, comment="拒绝原因"
    )

    # ── 借阅(borrow)业务字段 ──
    borrowed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, comment="借出时间")
    due_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True, comment="应还日期")
    returned_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, comment="归还时间")
    # ── 复制(copy)业务字段 ──
    copy_method: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, comment="复制方式: scan/photocopy/photo")
    copies: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="复制份数")
    fee: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True, comment="复制费用")
    delivered_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, comment="复制交付时间")
    # ── 证明(certificate)业务字段 ──
    cert_no: Mapped[Optional[str]] = mapped_column(String(40), nullable=True, comment="证明编号")
    cert_content: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="证明事项/内容")
    issued_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, comment="证明出具时间")

    tenant_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("iam_tenant.id", ondelete="CASCADE"),
        nullable=True, index=True
    )

    @property
    def biz_status(self) -> Optional[str]:
        """按利用方式推导的业务子状态（read 无,返回 None）。"""
        if self.use_type == "borrow":
            if self.returned_at:
                return "已归还"
            if self.borrowed_at:
                return "逾期" if (self.due_date and self.due_date < date.today()) else "借出中"
            return "待借出"
        if self.use_type == "copy":
            return "已交付" if self.delivered_at else "待复制"
        if self.use_type == "certificate":
            return "已出具" if self.issued_at else "待开具"
        return None


class UtilizationItem(BaseEntity):
    """
    调阅篮条目（利用申请下，利用人想调阅的一件档案）。

    archive_id 无 DB FK 约束（可指向暂存/正式库）；冗余 DH/TM 快照便于台账与凭证展示。
    """
    __tablename__ = "util_item"

    application_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("util_application.id", ondelete="CASCADE"),
        nullable=False, index=True, comment="所属利用申请"
    )
    archive_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True, comment="档案 ID（无 DB FK）"
    )
    DH: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, comment="档号快照")
    TM: Mapped[str] = mapped_column(String(512), nullable=False, comment="题名快照")
    RZZ: Mapped[Optional[str]] = mapped_column(String(200), nullable=True, comment="责任者快照")
    ND: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="年度快照")
    QZH: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, comment="全宗号快照")
    tenant_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("iam_tenant.id", ondelete="CASCADE"),
        nullable=True, index=True
    )
