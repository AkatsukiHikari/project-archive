"""档案保管：库房 / 架位 / 出入库记录。

StorageVault   库房（含架体网格布局 rows×columns×layers，为 three.js 三维渲染预留）
StorageShelf   架位（库房网格中的单个货架，记录占用率，供三维着色与架位详情）
StorageInout   出入库记录（借阅/修复/数字化/移库/盘点）；借阅出库由利用模块自动生成
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.common.entity.base import BaseEntity


class StorageVault(BaseEntity):
    __tablename__ = "stor_vault"

    code: Mapped[str] = mapped_column(
        String(40), nullable=False, index=True, comment="库房编号"
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="库房名称")
    location: Mapped[Optional[str]] = mapped_column(
        String(200), nullable=True, comment="位置（楼层/区域）"
    )
    area_sqm: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True, comment="面积（㎡）"
    )

    # 架体网格布局（三维渲染：rows 排 × columns 列 × layers 层）
    rows: Mapped[int] = mapped_column(
        Integer, nullable=False, default=4, comment="排数"
    )
    columns: Mapped[int] = mapped_column(
        Integer, nullable=False, default=6, comment="每排列数"
    )
    layers: Mapped[int] = mapped_column(
        Integer, nullable=False, default=5, comment="每列层数"
    )

    capacity: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="设计容量（卷/件）"
    )
    used: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="已用（卷/件）"
    )

    temperature: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True, comment="当前温度（℃）"
    )
    humidity: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True, comment="当前湿度（%RH）"
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="active",
        comment="状态: active 在用 | maintenance 维护 | disabled 停用",
    )
    manager_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("iam_user.id", ondelete="SET NULL"),
        nullable=True,
        comment="库房管理员",
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="备注")
    tenant_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("iam_tenant.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )


class StorageShelf(BaseEntity):
    """架位：库房网格中的单个货架（row_index 排、col_index 列）。"""

    __tablename__ = "stor_shelf"

    vault_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("stor_vault.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    code: Mapped[str] = mapped_column(
        String(40), nullable=False, comment="架位号，如 A-01-03"
    )
    row_index: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="排序号（0基）"
    )
    col_index: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="列序号（0基）"
    )
    capacity: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="架位容量"
    )
    used: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="已用"
    )
    label: Mapped[Optional[str]] = mapped_column(
        String(200), nullable=True, comment="存放范围标注"
    )
    tenant_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("iam_tenant.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )


class StorageInout(BaseEntity):
    """出入库记录。借阅出库由利用模块办理"借出"时自动生成，归还时回写。"""

    __tablename__ = "stor_inout"

    record_no: Mapped[str] = mapped_column(
        String(40), nullable=False, index=True, comment="出入库单号"
    )
    direction: Mapped[str] = mapped_column(
        String(10), nullable=False, index=True, comment="方向: out 出库 | in 入库"
    )
    biz_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="borrow",
        comment="业务类型: borrow 借阅 | repair 修复 | digitize 数字化 | relocate 移库 | inventory 盘点 | other",
    )
    archive_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True, comment="档案 ID（无 DB FK）"
    )
    DH: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, comment="档号快照"
    )
    TM: Mapped[Optional[str]] = mapped_column(
        String(512), nullable=True, comment="题名快照"
    )
    qty: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, comment="数量（卷/件）"
    )

    vault_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("stor_vault.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="所属库房",
    )
    counterparty: Mapped[Optional[str]] = mapped_column(
        String(200), nullable=True, comment="借出对象 / 经办对象"
    )
    related_app_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
        comment="关联利用申请 ID（借阅，无 DB FK）",
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="out",
        index=True,
        comment="状态: out 在外 | returned 已归还 | done 已完成（入库类）",
    )
    out_time: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="出库时间"
    )
    expected_return: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="应还时间"
    )
    in_time: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="归还/入库时间"
    )

    operator_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("iam_user.id", ondelete="SET NULL"),
        nullable=True,
        comment="经办人",
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="备注")
    tenant_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("iam_tenant.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
