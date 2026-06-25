"""
AI Tool 回调路由（Dify → 后端）

⚠️ 这些端点**不挂 get_current_user**：调用方是 Dify Workflow，没有用户登录态。
我们靠两层凭证恢复身份：
1. ``X-Service-Token``：Dify 与后端的服务级共享密钥（防止外网直连）
2. ``X-User-Token``：chat 入口签发的短 TTL JWT，恢复用户身份 + 场景

端点：
- POST /v1/ai/internal/retrieve         检索代理（meta / rules / ocr）
- POST /v1/ai/internal/tool/dispatch    通用 Tool 分发占位（P3 写类能力扩这里）
"""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any, Literal

logger = logging.getLogger(__name__)

from fastapi import APIRouter, Depends, Header, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.error_code import ErrorCode
from app.common.exceptions.base import BaseAPIException
from app.common.response import ResponseModel
from app.infra.db.session import get_db
from app.modules.ai.constants import AUDIT_AI_TOOL_CALL
from app.modules.ai.services.capabilities import \
    dispatch as capability_dispatch
from app.modules.ai.services.capabilities import get_capability
from app.modules.ai.services.capabilities.types import CapabilityContext
from app.modules.ai.services.retrieval_service import (
    KBType, RetrievalService, RetrievalUnavailableError, RetrieveFilter)
from app.modules.ai.services.user_token import (AIUserTokenClaims,
                                                verify_service_token,
                                                verify_user_token)
from app.modules.audit.repositories.audit_repository import \
    SQLAlchemyAuditRepository
from app.modules.audit.schemas.audit_log import AuditLogCreate
from app.modules.audit.services.audit_service import AuditService

router = APIRouter()


# ── 凭证恢复依赖 ────────────────────────────────────────────────────────────


async def restore_claims(
    x_user_token: str | None = Header(default=None, alias="X-User-Token"),
    x_service_token: str | None = Header(default=None, alias="X-Service-Token"),
) -> AIUserTokenClaims:
    # 服务令牌：放行已配置租户级 ingress
    verify_service_token(x_service_token)
    if not x_user_token:
        raise BaseAPIException(
            code=ErrorCode.AI_TOOL_AUTH_FAILED,
            message="缺少 X-User-Token",
            status_code=401,
        )
    return verify_user_token(x_user_token)


# ── /retrieve ──────────────────────────────────────────────────────────────


class RetrieveRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    kb_type: Literal["meta", "rules", "ocr"] = "meta"
    top_k: int = Field(default=5, ge=1, le=50)
    # 下列字段保留以兼容 Dify 传参，但**全部忽略**——租户/密级只信 JWT
    tenant_id_hint: str | None = None
    secret_level_hint: int | None = None


class RetrievedChunkOut(BaseModel):
    chunk_id: str
    source_type: str
    source_id: str
    title: str
    snippet: str
    score: float
    secret_level: int
    tenant_id: str
    category_id: str | None = None
    extra: dict[str, Any] | None = None


class RetrieveResponse(BaseModel):
    chunks: list[RetrievedChunkOut]


@router.post(
    "/retrieve",
    summary="Dify 检索代理",
    description="Dify Workflow 调本端点拉取知识库片段；权限 filter 由后端强制注入，**忽略**请求体里的任何过滤参数。",
    response_model=ResponseModel[RetrieveResponse],
)
async def retrieve(
    request: Request,
    body: RetrieveRequest,
    claims: AIUserTokenClaims = Depends(restore_claims),
    db: AsyncSession = Depends(get_db),
) -> ResponseModel[RetrieveResponse]:
    filt = RetrieveFilter(
        tenant_id=uuid.UUID(claims.tenant_id),
        secret_level=claims.secret_level,
        user_id=uuid.UUID(claims.user_id),
    )
    svc = RetrievalService(db)
    chunks = await svc.retrieve(
        query=body.query,
        kb_type=body.kb_type,
        top_k=body.top_k,
        filt=filt,
    )

    # 审计：每次 Tool 回调都落日志（设计稿 §7.3）
    try:
        audit_svc = AuditService(SQLAlchemyAuditRepository(db))
        await audit_svc.create_audit_log(
            AuditLogCreate(
                user_id=uuid.UUID(claims.user_id),
                tenant_id=uuid.UUID(claims.tenant_id),
                action=AUDIT_AI_TOOL_CALL,
                module="ai",
                ip_address=request.client.host if request.client else None,
                status="SUCCESS",
                details={
                    "tool": "retrieve",
                    "kb_type": body.kb_type,
                    "top_k": body.top_k,
                    "query": body.query[:200],
                    "scenario_code": claims.scenario_code,
                    "hits": len(chunks),
                },
            )
        )
    except Exception:
        # 审计失败不阻断 Dify 调用
        pass

    out = [
        RetrievedChunkOut(
            chunk_id=c.chunk_id,
            source_type=c.source_type,
            source_id=c.source_id,
            title=c.title,
            snippet=c.snippet,
            score=c.score,
            secret_level=c.secret_level,
            tenant_id=c.tenant_id,
            category_id=c.category_id,
            extra=c.extra,
        )
        for c in chunks
    ]
    return ResponseModel(data=RetrieveResponse(chunks=out))


# ── /tool/dispatch ─────────────────────────────────────────────────────────


class ToolDispatchRequest(BaseModel):
    """通用 Tool 分发请求。"""

    tool_name: str = Field(default="", max_length=128)
    fallback_tool_name: str = Field(default="", max_length=128)
    arguments: dict[str, Any] = Field(default_factory=dict)


# Classifier label / 中文名 → capability code 的兜底映射
_CLASSIFIER_LABEL_TO_CODE: dict[str, str] = {
    "问答": "qa",
    "检索": "search",
    "综述": "summary",
    "挂接": "attach",
    "编目": "catalog",
    "四性": "fournat",
    "拟稿": "draft",
    "关联": "relate",
    "知识库": "kb_manage",
}


def _resolve_tool_name(primary: str, fallback: str) -> str:
    """优先用 primary（前端 scenario_hint）；为空才尝试 fallback（Classifier 的 class_name）。"""
    for candidate in (primary, fallback):
        if not candidate:
            continue
        # 已经是 capability code
        if get_capability(candidate):
            return candidate
        # 形如「问答（基于...）」抽出前缀，再映射
        head = candidate.split("（")[0].strip()
        if head in _CLASSIFIER_LABEL_TO_CODE:
            return _CLASSIFIER_LABEL_TO_CODE[head]
    return ""


class ToolDispatchResponse(BaseModel):
    tool_name: str
    status: Literal["accepted", "rejected", "not_implemented"]
    detail: str | None = None
    result: dict[str, Any] | None = None


@router.post(
    "/tool/dispatch",
    summary="Dify Tool 通用分发（A' 方案核心入口）",
    description=(
        "Dify 主 Chatflow 的 HTTP 节点把意图分类结果发到这里；"
        "本端点按 ``tool_name``（=scenario_code）路由到 8 个 capability service。"
    ),
    response_model=ResponseModel[ToolDispatchResponse],
)
async def dispatch_tool(
    request: Request,
    claims: AIUserTokenClaims = Depends(restore_claims),
    db: AsyncSession = Depends(get_db),
) -> ResponseModel[ToolDispatchResponse]:
    # 容忍 Dify HTTP 节点的非标 body 形态
    raw = await request.body()
    print(
        f"[dispatch] raw ({len(raw)} bytes): {raw.decode('utf-8', errors='replace')[:600]}",
        flush=True,
    )
    try:
        payload = json.loads(raw) if raw else {}
    except json.JSONDecodeError:
        payload = {}
    # Dify json body 可能反序列化为 list of dict（每项是一个 key/value 对）
    if isinstance(payload, list):
        merged: dict = {}
        for item in payload:
            if isinstance(item, dict):
                merged.update(item)
        payload = merged
    if not isinstance(payload, dict):
        payload = {}
    body = ToolDispatchRequest(
        tool_name=str(payload.get("tool_name", "") or ""),
        fallback_tool_name=str(payload.get("fallback_tool_name", "") or ""),
        arguments=payload.get("arguments") or {},
    )
    # 审计：尝试调用本身就是事件
    try:
        audit_svc = AuditService(SQLAlchemyAuditRepository(db))
        await audit_svc.create_audit_log(
            AuditLogCreate(
                user_id=uuid.UUID(claims.user_id),
                tenant_id=uuid.UUID(claims.tenant_id),
                action=AUDIT_AI_TOOL_CALL,
                module="ai",
                ip_address=request.client.host if request.client else None,
                status="SUCCESS",
                details={
                    "tool": body.tool_name,
                    "scenario_code": claims.scenario_code,
                    "args_keys": sorted(list(body.arguments.keys()))[:20],
                },
            )
        )
    except Exception:
        pass

    # ── 真实分发 ──
    resolved_code = _resolve_tool_name(body.tool_name, body.fallback_tool_name)
    if not resolved_code:
        return ResponseModel(
            data=ToolDispatchResponse(
                tool_name=body.tool_name or body.fallback_tool_name,
                status="not_implemented",
                detail=(
                    f"未能映射到 capability code: tool_name={body.tool_name!r} "
                    f"fallback={body.fallback_tool_name!r}"
                ),
            )
        )

    ctx = CapabilityContext(
        tenant_id=uuid.UUID(claims.tenant_id),
        user_id=uuid.UUID(claims.user_id),
        secret_level=claims.secret_level,
        scenario_code=resolved_code,
    )
    query = str(body.arguments.get("query") or "")
    result = await capability_dispatch(db=db, ctx=ctx, code=resolved_code, query=query)

    return ResponseModel(
        data=ToolDispatchResponse(
            tool_name=resolved_code,
            status=(
                "accepted" if result.status == "ok" else (result.status or "rejected")
            ),
            detail=result.reason,
            result={
                "answer": result.answer,
                "citations": result.citations,
                "patch_id": str(result.patch_id) if result.patch_id else None,
                **result.detail,
            },
        )
    )


# ── /tool/dispatch_text：Dify 主 Chatflow 简化端点（返回 plain markdown text） ──

from fastapi.responses import PlainTextResponse


@router.post(
    "/tool/dispatch_text",
    summary="Dify 简化调用入口（返回 plain text answer）",
    description="主 Chatflow 的 HTTP 节点用此端点；body 直接是 markdown 文本，可作为 Answer 节点输出，绕开 LLM 的编造问题。",
    response_class=PlainTextResponse,
)
async def dispatch_tool_text(
    request: Request,
    claims: AIUserTokenClaims = Depends(restore_claims),
    db: AsyncSession = Depends(get_db),
) -> PlainTextResponse:
    raw = await request.body()
    try:
        payload = json.loads(raw) if raw else {}
    except json.JSONDecodeError:
        payload = {}
    if isinstance(payload, list):
        merged: dict = {}
        for item in payload:
            if isinstance(item, dict):
                merged.update(item)
        payload = merged
    if not isinstance(payload, dict):
        payload = {}

    code = _resolve_tool_name(
        str(payload.get("tool_name", "") or ""),
        str(payload.get("fallback_tool_name", "") or ""),
    )
    if not code:
        return PlainTextResponse(
            content="未能识别用户意图，请补充关键词或重新提问。",
            media_type="text/markdown; charset=utf-8",
        )

    query = str((payload.get("arguments") or {}).get("query") or "")
    ctx = CapabilityContext(
        tenant_id=uuid.UUID(claims.tenant_id),
        user_id=uuid.UUID(claims.user_id),
        secret_level=claims.secret_level,
        scenario_code=code,
    )
    try:
        result = await capability_dispatch(db=db, ctx=ctx, code=code, query=query)
    except RetrievalUnavailableError:
        # 检索后端故障：老实报"暂不可用"，绝不伪装成"查无此档"误导用户
        logger.warning(
            "dispatch_text 检索服务不可用 code=%s query=%r", code, query[:80]
        )
        return PlainTextResponse(
            content="档案检索服务暂时不可用，请稍后重试。（系统已记录该故障）",
            media_type="text/markdown; charset=utf-8",
        )
    return PlainTextResponse(
        content=result.answer or "未在档案库中找到相关内容。",
        media_type="text/markdown; charset=utf-8",
    )


# ── /capability/{code}：子 Workflow 的 HTTP 节点直接调用 ──────────────────────


class CapabilityRequest(BaseModel):
    """子 Workflow HTTP 节点请求体。"""

    query: str = Field(..., max_length=4096)
    tenant_id: str | None = Field(default=None, description="忽略，从 token 取")


class CapabilityResponse(BaseModel):
    code: str
    status: str
    answer: str
    citations: list[dict] = []
    patch_id: str | None = None
    detail: dict = {}


@router.post(
    "/capability/{code}",
    summary="子 Workflow 直接调用能力 service",
    response_model=ResponseModel[CapabilityResponse],
)
async def call_capability(
    code: str,
    request: Request,
    body: CapabilityRequest,
    claims: AIUserTokenClaims = Depends(restore_claims),
    db: AsyncSession = Depends(get_db),
) -> ResponseModel[CapabilityResponse]:
    runner = get_capability(code)
    if runner is None:
        raise BaseAPIException(
            code=ErrorCode.AI_CAPABILITY_DISABLED,
            message=f"未识别的能力: {code}",
            status_code=400,
        )

    ctx = CapabilityContext(
        tenant_id=uuid.UUID(claims.tenant_id),
        user_id=uuid.UUID(claims.user_id),
        secret_level=claims.secret_level,
        scenario_code=code,
    )
    result = await capability_dispatch(db=db, ctx=ctx, code=code, query=body.query)
    return ResponseModel(
        data=CapabilityResponse(
            code=code,
            status=result.status,
            answer=result.answer,
            citations=result.citations,
            patch_id=str(result.patch_id) if result.patch_id else None,
            detail=result.detail,
        )
    )
