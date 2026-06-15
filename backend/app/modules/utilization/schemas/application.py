import uuid
from datetime import datetime, date
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


# ── 利用申请 ──────────────────────────────────────────────────────────────────

class ApplicationCreate(BaseModel):
    applicant_name: str = Field(..., max_length=100)
    id_card_no: Optional[str] = Field(default=None, max_length=32)
    gender: Optional[str] = Field(default=None, max_length=8)
    phone: Optional[str] = Field(default=None, max_length=32)
    organization: Optional[str] = Field(default=None, max_length=200)
    purpose: Optional[str] = None
    use_type: str = "read"
    avatar_key: Optional[str] = None


class ApplicationUpdate(BaseModel):
    applicant_name: Optional[str] = Field(default=None, max_length=100)
    id_card_no: Optional[str] = None
    gender: Optional[str] = None
    phone: Optional[str] = None
    organization: Optional[str] = None
    purpose: Optional[str] = None
    use_type: Optional[str] = None


class ApplicationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    reg_no: str
    applicant_name: str
    id_card_no: Optional[str] = None
    gender: Optional[str] = None
    phone: Optional[str] = None
    organization: Optional[str] = None
    avatar_key: Optional[str] = None
    purpose: Optional[str] = None
    use_type: str
    status: str
    handler_id: Optional[uuid.UUID] = None
    completed_at: Optional[datetime] = None
    create_time: datetime
    item_count: int = 0          # 调阅篮件数
    handler_name: Optional[str] = None

    # 业务字段（按 use_type 使用）
    borrowed_at: Optional[datetime] = None
    due_date: Optional[date] = None
    returned_at: Optional[datetime] = None
    copy_method: Optional[str] = None
    copies: Optional[int] = None
    fee: Optional[float] = None
    delivered_at: Optional[datetime] = None
    cert_no: Optional[str] = None
    cert_content: Optional[str] = None
    issued_at: Optional[datetime] = None
    biz_status: Optional[str] = None   # 子状态：待借出/借出中/逾期/已归还/待复制/已交付/待开具/已出具


# ── 办理动作 ──────────────────────────────────────────────────────────────────

class BorrowLendRequest(BaseModel):
    due_date: date


class BorrowRenewRequest(BaseModel):
    due_date: date


class CopyProcessRequest(BaseModel):
    copy_method: str = "scan"
    copies: int = Field(default=1, ge=1)
    fee: Optional[float] = None


class CertIssueRequest(BaseModel):
    cert_content: str = Field(..., min_length=1)


# ── 调阅篮条目 ────────────────────────────────────────────────────────────────

class ItemIn(BaseModel):
    archive_id: uuid.UUID
    DH: Optional[str] = None
    TM: str
    RZZ: Optional[str] = None
    ND: Optional[int] = None
    QZH: Optional[str] = None


class ItemsAdd(BaseModel):
    items: list[ItemIn]


class ItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    archive_id: uuid.UUID
    DH: Optional[str] = None
    TM: str
    RZZ: Optional[str] = None
    ND: Optional[int] = None
    QZH: Optional[str] = None
    has_attachment: bool = False  # 是否有原文（无则前端禁用"原文"按钮）
    create_time: datetime


class ApplicationDetail(ApplicationOut):
    items: list[ItemOut] = Field(default_factory=list)
