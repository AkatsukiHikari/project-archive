from sqlalchemy import String, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.common.entity.base import BaseEntity
from typing import Optional
import uuid

class AuditLog(BaseEntity):
    __tablename__ = "iam_audit_log"
    
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("iam_user.id", ondelete="SET NULL"), nullable=True, index=True, comment="操作用户ID")
    tenant_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("iam_tenant.id", ondelete="SET NULL"), nullable=True, index=True, comment="所属租户ID")
    
    action: Mapped[str] = mapped_column(String(100), index=True, comment="操作动作 (例如: 'USER_LOGIN', 'DELETE_ARCHIVE')")
    module: Mapped[str] = mapped_column(String(50), index=True, comment="功能模块 (例如: 'IAM', 'ARCHIVE')")
    ip_address: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, comment="IP地址")
    user_agent: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, comment="用户代理解析")
    
    status: Mapped[str] = mapped_column(String(20), default="SUCCESS", comment="状态: SUCCESS, FAILED")
    details: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True, comment="结构化操作详情 (JSON)")
    error_message: Mapped[Optional[str]] = mapped_column(String(500), nullable=True, comment="错误信息")
    
    # Navigation properties are optional depending on if we need to query user from log
    # For now, we can leave them out to avoid circular dependencies unless necessary.
