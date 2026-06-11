"""四性检测：检测项目录 + 检测方案 模型。

设计：检测项(原子·带标准依据·rule/ai/manual)→ 方案(组合·必检否决·参数覆盖)。
目录为全局(不分租户),方案可分租户。
"""
import uuid
from typing import Optional

from sqlalchemy import String, Integer, Boolean, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.common.entity.base import BaseEntity


class CheckItem(BaseEntity):
    """检测项目录（最小原子检测单元，供方案勾选）。"""
    __tablename__ = "pres_check_item"

    code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True, comment="检测项编码")
    name: Mapped[str] = mapped_column(String(200), nullable=False, comment="检测项名称")
    dimension: Mapped[str] = mapped_column(
        String(20), nullable=False, index=True,
        comment="四性维度: authenticity 真实 | integrity 完整 | usability 可用 | safety 安全",
    )
    exec_type: Mapped[str] = mapped_column(
        String(10), nullable=False, default="rule",
        comment="执行方式: rule 规则自动 | ai AI自动 | manual 人工核验",
    )
    standard_ref: Mapped[Optional[str]] = mapped_column(String(200), nullable=True, comment="依据标准条款，如 DA/T 70-2018 §5.2")
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="检测内容说明")
    carrier_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="electronic",
        comment="适用载体: electronic 电子 | paper 纸质 | av 音视频 | all",
    )
    default_params: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True, comment="默认参数")
    default_weight: Mapped[int] = mapped_column(Integer, nullable=False, default=10, comment="默认权重")
    default_blocking: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, comment="默认是否必检(一票否决)")
    builtin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, comment="是否内置(国标)")
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, comment="目录中是否启用")


class DetectionScheme(BaseEntity):
    """四性检测方案（检测项的有序勾选 + 配置）。"""
    __tablename__ = "pres_scheme"

    name: Mapped[str] = mapped_column(String(200), nullable=False, comment="方案名称")
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="说明")
    carrier_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="electronic", comment="适用载体"
    )
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, comment="是否默认方案")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, comment="版本")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active", comment="active | disabled")
    tenant_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("iam_tenant.id", ondelete="CASCADE"), nullable=True, index=True
    )


class SchemeItem(BaseEntity):
    """方案-检测项关联（每项的启用/参数/权重/是否必检/顺序）。"""
    __tablename__ = "pres_scheme_item"

    scheme_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("pres_scheme.id", ondelete="CASCADE"), nullable=False, index=True
    )
    check_code: Mapped[str] = mapped_column(String(64), nullable=False, comment="检测项编码(引用 pres_check_item.code)")
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    params: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True, comment="参数覆盖")
    weight: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    is_blocking: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, comment="必检(一票否决)")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
