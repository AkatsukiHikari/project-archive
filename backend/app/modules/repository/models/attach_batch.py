"""数字化成果挂接批次（留痕 + 报表）。

每次批量挂接 = 一个批次，记录 成功/跳过/无匹配 计数与逐文件明细，
供挂接历史查询与导出追溯。
"""
import uuid
from typing import Optional

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.common.entity.base import BaseEntity


class AttachBatch(BaseEntity):
    __tablename__ = "repo_attach_batch"

    batch_no: Mapped[str] = mapped_column(
        String(40), nullable=False, index=True, comment="批次号 GJyyyymmddNNN"
    )
    total: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="文件总数")
    attached: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="挂接成功数")
    skipped: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="跳过数")
    not_found: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="无匹配档号数")
    overwrite: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, comment="是否覆盖已有原文")
    rows: Mapped[Optional[list]] = mapped_column(
        JSONB, nullable=True, comment="逐文件明细 [{filename,DH,status,TM,source,reason}]"
    )
    operator_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("iam_user.id", ondelete="SET NULL"),
        nullable=True, comment="操作人"
    )
    tenant_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("iam_tenant.id", ondelete="CASCADE"),
        nullable=True, index=True
    )
