"""
引用校验器

设计稿 §7.2：
- 每条 AI 输出必须挂 ``citations[]``（无证据则拒答）
- 引用的 chunk 必须在用户权限范围内（tenant / 密级 / 类目）
- 越权引用：整段答案替换为 "出处校验失败，已上报"，并写审计

P1：先把接口骨架立起来。真实的 chunk 权属查询要靠 retrieval_service 给的元数据
+ archive / fonds / category 这一系列业务表，本期先做"形态校验 + tenant/密级粗粒度校验"，
档案级细粒度校验留 P2 拉档案表落实。
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ValidationOutcome:
    """校验结果。

    ``valid=False`` 时调用方应当替换答案为"出处校验失败"。
    """

    valid: bool
    rejected: tuple[str, ...]  # 被拒绝的 chunk_id 列表
    accepted: tuple[dict[str, Any], ...]  # 合规的引用，原样回传给前端
    reason: str | None = None  # 拒绝原因（人类可读）


class CitationValidator:
    """检查 citations 是否在调用方用户的权限范围内。"""

    def __init__(
        self,
        *,
        tenant_id: uuid.UUID | str,
        user_secret_level: int,
        require_citation: bool,
    ):
        self._tenant_id = str(tenant_id)
        self._level = user_secret_level
        self._require = require_citation

    def validate(self, citations: list[dict[str, Any]] | None) -> ValidationOutcome:
        items = list(citations or [])

        if not items:
            if self._require:
                return ValidationOutcome(
                    valid=False,
                    rejected=(),
                    accepted=(),
                    reason="未携带引用且场景强制要求引用",
                )
            return ValidationOutcome(valid=True, rejected=(), accepted=())

        accepted: list[dict[str, Any]] = []
        rejected: list[str] = []
        for c in items:
            if not self._has_required_keys(c):
                rejected.append(str(c.get("chunk_id", "?")))
                continue
            chunk_tenant = str(c.get("tenant_id") or "")
            chunk_level = int(c.get("secret_level") or 0)
            if chunk_tenant and chunk_tenant != self._tenant_id:
                rejected.append(str(c.get("chunk_id")))
                continue
            if chunk_level > self._level:
                rejected.append(str(c.get("chunk_id")))
                continue
            accepted.append(c)

        if rejected:
            logger.warning(
                "citation_validator 拦截越权引用：rejected=%s tenant=%s level=%d",
                rejected,
                self._tenant_id,
                self._level,
            )
            # 一票否决：越权一条就整段失败（设计稿明确）
            return ValidationOutcome(
                valid=False,
                rejected=tuple(rejected),
                accepted=tuple(accepted),
                reason="存在越权引用：" + ", ".join(rejected),
            )

        return ValidationOutcome(valid=True, rejected=(), accepted=tuple(accepted))

    @staticmethod
    def _has_required_keys(citation: dict[str, Any]) -> bool:
        return "chunk_id" in citation and "source_type" in citation
