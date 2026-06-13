"""鉴定标准条款 + 敏感词库 模型。

开放鉴定的依据数据，后台可维护：
  appr_standard        划控/开放标准条款（命中关键词或 LLM 语义匹配后，导向某个开放状态结论）
  appr_sensitive_word  敏感词（题名/责任者/扩展字段命中即建议控制类结论）
"""

import uuid
from typing import Optional

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.common.entity.base import BaseEntity


class AppraisalStandard(BaseEntity):
    """鉴定标准条款（开放/划控依据，结论理由引用其内容）。"""

    __tablename__ = "appr_standard"

    code: Mapped[str] = mapped_column(
        String(40), nullable=False, index=True, comment="条款编码，如 KF-01 / KZ-03"
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False, comment="条款名称")
    content: Mapped[str] = mapped_column(
        Text, nullable=False, comment="条款内容（结论理由引用）"
    )
    target_kfzt: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="导向结论: 开放 | 控制使用 | 延期开放 | 不开放",
    )
    keywords: Mapped[Optional[list]] = mapped_column(
        JSONB, nullable=True, comment="匹配关键词列表（命中即建议该条款结论）"
    )
    source: Mapped[Optional[str]] = mapped_column(
        String(200), nullable=True, comment="出处，如《国家档案馆档案开放办法》第十二条"
    )
    is_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, comment="是否启用"
    )
    sort_order: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="排序号"
    )
    tenant_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("iam_tenant.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )


class AppraisalSensitiveWord(BaseEntity):
    """敏感词（AI 预鉴定的确定性扫描依据）。"""

    __tablename__ = "appr_sensitive_word"

    word: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True, comment="敏感词"
    )
    category: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, comment="类别: 国家安全 | 个人隐私 | 商业秘密 | …"
    )
    suggest_kfzt: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="控制使用",
        comment="命中后建议结论: 控制使用 | 延期开放 | 不开放",
    )
    is_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, comment="是否启用"
    )
    tenant_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("iam_tenant.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
