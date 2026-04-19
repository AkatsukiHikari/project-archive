import uuid
from sqlalchemy import String, Integer, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.common.entity.base import BaseEntity


class ArchiveNoSeq(BaseEntity):
    """
    档号序号跟踪表。
    每条记录代表某规则在某 scope_key 下的当前最大序号。
    并发安全：写入时使用 SELECT ... FOR UPDATE 锁行后递增。
    """
    __tablename__ = "repo_archive_no_seq"
    __table_args__ = (
        UniqueConstraint("rule_id", "scope_key", name="uq_no_seq_rule_scope"),
    )

    rule_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("repo_archive_no_rule.id", ondelete="CASCADE"),
        nullable=False, index=True, comment="所属规则"
    )
    scope_key: Mapped[str] = mapped_column(
        String(200), nullable=False,
        comment="序号范围键，如 catalog_year:<catalog_id>:<year>"
    )
    current_seq: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="当前已分配的最大序号"
    )
