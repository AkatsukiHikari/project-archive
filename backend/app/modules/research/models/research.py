"""档案编研：项目 / 素材 / 成果。

编研 = 以馆藏档案为对象，研究内容 + 编辑加工成系统性成果。
  ResearchProject  编研项目（立项 + 流程容器）
  ResearchMaterial 项目素材（从档案库选材，关联源档案）
  ResearchResult   编研成果（大事记/组织沿革/专题汇编/参考资料… 引用源档案）

编研类型(project_type / result_type)：
  大事记 | 组织沿革 | 专题汇编 | 基础数字汇编 | 参考资料 | 全宗指南
"""

import uuid
from datetime import date, datetime
from typing import Optional

from sqlalchemy import (Boolean, Date, DateTime, ForeignKey, Integer, String,
                        Text)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.common.entity.base import BaseEntity


class ResearchProject(BaseEntity):
    __tablename__ = "research_project"

    title: Mapped[str] = mapped_column(String(200), nullable=False, comment="项目题名")
    project_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="专题汇编",
        comment="编研类型: 大事记|组织沿革|专题汇编|基础数字汇编|参考资料|全宗指南",
    )
    editor_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("iam_user.id", ondelete="SET NULL"),
        nullable=True,
        comment="主编",
    )
    reviewer_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("iam_user.id", ondelete="SET NULL"),
        nullable=True,
        comment="审核人",
    )
    members: Mapped[Optional[list]] = mapped_column(
        JSONB, nullable=True, comment="编辑成员姓名列表"
    )
    start_date: Mapped[Optional[date]] = mapped_column(
        Date, nullable=True, comment="起始日期"
    )
    end_date: Mapped[Optional[date]] = mapped_column(
        Date, nullable=True, comment="计划完成日期"
    )
    purpose: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="编研目的/简介"
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="in_progress",
        comment="in_progress 进行中 | completed 已完成",
    )
    tenant_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("iam_tenant.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )


class ResearchTemplate(BaseEntity):
    """编研模板：成果文档的可复用骨架（内置 + 用户自存），用于"快速开始"。"""

    __tablename__ = "research_template"

    name: Mapped[str] = mapped_column(String(200), nullable=False, comment="模板名称")
    result_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="专题汇编", comment="适用编研类型"
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="模板说明"
    )
    content: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="模板正文 HTML"
    )
    content_json: Mapped[Optional[dict]] = mapped_column(
        JSONB, nullable=True, comment="模板文档 JSON"
    )
    is_builtin: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, comment="系统内置模板（不可删）"
    )
    sort_order: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="排序"
    )
    tenant_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("iam_tenant.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="租户（内置模板为空，全局可见）",
    )


class ResearchMaterial(BaseEntity):
    """项目素材：选入项目的源档案（无 DB FK，冗余快照便于展示与编纂）。"""

    __tablename__ = "research_material"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("research_project.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    archive_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True, comment="源档案 ID（无 DB FK）"
    )
    DH: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, comment="档号快照"
    )
    TM: Mapped[str] = mapped_column(String(512), nullable=False, comment="题名快照")
    RZZ: Mapped[Optional[str]] = mapped_column(
        String(200), nullable=True, comment="责任者快照"
    )
    ND: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, comment="年度快照"
    )
    WJRQ: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True, comment="文件日期快照"
    )
    QZH: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, comment="全宗号快照"
    )
    tenant_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("iam_tenant.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )


class ResearchResultArchive(BaseEntity):
    """成果档案库：成果自有的引用档案集（从馆藏选入，存冗余快照）。

    正文里的引文标记按 archive_id 关联到这里的条目，可生成"引用档案目录"。
    """

    __tablename__ = "research_result_archive"

    result_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("research_result.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    archive_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True, comment="源档案 ID（无 DB FK）"
    )
    DH: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, comment="档号快照"
    )
    TM: Mapped[str] = mapped_column(String(512), nullable=False, comment="题名快照")
    RZZ: Mapped[Optional[str]] = mapped_column(
        String(200), nullable=True, comment="责任者快照"
    )
    ND: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, comment="年度快照"
    )
    WJRQ: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True, comment="文件日期快照"
    )
    QZH: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, comment="全宗号快照"
    )
    sort_order: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="引用序号"
    )
    tenant_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("iam_tenant.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )


class ResearchResult(BaseEntity):
    """编研成果。content 存正文 HTML（类 Word 在线文档）；content_json 存编辑器原生
    文档 JSON（无损再编辑）。引用档案见 ResearchResultArchive（成果自有档案库）。"""

    __tablename__ = "research_result"

    project_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("research_project.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="所属编研项目",
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False, comment="成果题名")
    result_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="专题汇编", comment="编研成果类型"
    )
    summary: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="内容提要"
    )
    content: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="正文 HTML（用于展示/导出）"
    )
    content_json: Mapped[Optional[dict]] = mapped_column(
        JSONB, nullable=True, comment="编辑器原生文档 JSON（用于无损再编辑）"
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="draft",
        index=True,
        comment="draft 草稿 | reviewing 待审 | finalized 定稿 | published 发布",
    )
    author_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("iam_user.id", ondelete="SET NULL"),
        nullable=True,
    )
    reviewer_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("iam_user.id", ondelete="SET NULL"),
        nullable=True,
    )
    finalized_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    published_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    tenant_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("iam_tenant.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
