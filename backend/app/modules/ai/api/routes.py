"""
AI 聊天 API 路由

端点：
- GET  /v1/ai/scenarios  — 列出当前租户启用的 AI 能力（前端 Tab 用）
- POST /v1/ai/chat       — 流式聊天（SSE），按场景 + 模型档位路由
"""

import json
import logging
import uuid

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.error_code import ErrorCode
from app.common.exceptions.base import BaseAPIException
from app.common.response import ResponseModel
from app.core.config import settings
from app.infra.db.session import get_db
from app.modules.ai._tenant_helper import \
    ensure_tenant_id as _ensure_tenant_id  # noqa: E402
from app.modules.ai.constants import AUDIT_AI_CHAT_QUERY
from app.modules.ai.models.ai_scenario import AIScenario
from app.modules.ai.models.ai_session import AISession
from app.modules.ai.schemas.chat import (ChatRequest, ScenarioInfo,
                                         ScenarioListResponse, SessionItem,
                                         SessionListResponse)
from app.modules.ai.services.answer_synth import synthesize_answer
from app.modules.ai.services.dify_service import dify_service
from app.modules.ai.services.retrieval_service import (
    RetrievalService, RetrievalUnavailableError, RetrieveFilter)
from app.modules.ai.services.scenario_router import (ALL_SCENARIO_CODES,
                                                     ScenarioRouter)
from app.modules.ai.services.session_service import SessionService
from app.modules.ai.services.user_token import sign_user_token
from app.modules.audit.repositories.audit_repository import \
    SQLAlchemyAuditRepository
from app.modules.audit.schemas.audit_log import AuditLogCreate
from app.modules.audit.services.audit_service import AuditService
from app.modules.iam.api.dependencies import get_current_user
from app.modules.iam.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter()


# 9 个场景的默认显示名（DB 未配置该租户时用作占位）
_SCENARIO_DISPLAY: dict[str, tuple[str, str]] = {
    "qa": ("智能问答", "基于档案知识库的检索增强问答"),
    "search": ("自然语言检索", "用自然语言描述需求，自动构造结构化检索"),
    "summary": ("档案摘要", "按主题/全宗/类目生成专题综述，强制引用"),
    "attach": ("自动挂接", "扫描批量入库内容并提议挂接到既有档案"),
    "catalog": ("自动编目", "OCR + 抽取 + 生号规则联动，产出编目 patch"),
    "fournat": ("四性建议", "真实性/完整性/可用性/安全性 风险点提示（建议态）"),
    "draft": ("拟稿", "鉴定意见/销毁建议/利用报告 草稿（建议态）"),
    "relate": ("关联分析", "跨档案/全宗的关联建议（建议态）"),
    "kb_manage": ("知识库管理", "查看索引状态、触发重建（写侧走 patch）"),
}


@router.get(
    "/scenarios",
    summary="列出 AI 能力（场景）",
    description="返回当前租户启用的 9 个 AI 能力的元信息，供前端渲染场景 Tab 和模型档位下拉。",
    response_model=ResponseModel[ScenarioListResponse],
)
async def list_scenarios(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ResponseModel[ScenarioListResponse]:
    enabled_codes = {
        c.strip()
        for c in (settings.AI_ENABLED_CAPABILITIES or "").split(",")
        if c.strip()
    }
    tenant_id = await _ensure_tenant_id(db, current_user)

    stmt = select(AIScenario).where(
        AIScenario.tenant_id == tenant_id,
        AIScenario.is_deleted.is_(False),
    )
    rows = (await db.execute(stmt)).scalars().all()
    row_by_code: dict[str, AIScenario] = {row.scenario_code: row for row in rows}

    scenarios: list[ScenarioInfo] = []
    for code in ALL_SCENARIO_CODES:
        display_name, description = _SCENARIO_DISPLAY.get(code, (code, None))
        row = row_by_code.get(code)
        if row is not None:
            scenarios.append(
                ScenarioInfo(
                    code=code,
                    name=row.name or display_name,
                    description=row.description or description,
                    enabled=row.enabled and code in enabled_codes,
                    default_model_tier=row.default_model_tier
                    or settings.AI_DEFAULT_MODEL_TIER,
                    gate=row.gate,
                    citation_required=row.citation_required,
                )
            )
        else:
            scenarios.append(
                ScenarioInfo(
                    code=code,
                    name=display_name,
                    description=description,
                    # 未配置时按全局灰度白名单回退；P1 demo 不依赖 seed
                    enabled=code in enabled_codes,
                    default_model_tier=settings.AI_DEFAULT_MODEL_TIER,
                    gate=settings.AI_PATCH_DEFAULT_GATE,
                    citation_required=settings.AI_CITATION_REQUIRED,
                )
            )

    # 按"价值递增 + 风险递增"原始顺序排（与设计稿一致）
    order = [
        "qa",
        "search",
        "summary",
        "attach",
        "catalog",
        "kb_manage",
        "fournat",
        "draft",
        "relate",
    ]
    scenarios.sort(key=lambda s: order.index(s.code) if s.code in order else 999)

    return ResponseModel(
        data=ScenarioListResponse(
            scenarios=scenarios,
            default_model_tier=settings.AI_DEFAULT_MODEL_TIER,
        )
    )


@router.post(
    "/chat",
    summary="档案智能对话（流式，按场景路由）",
    description="""
    与 AI 档案助手对话；按 ``scenario_code`` 路由到对应能力 + 模型档位。

    **响应格式**：Server-Sent Events (SSE)
    """,
)
async def chat(
    request: Request,
    body: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    user_id = str(current_user.id)
    tenant_id = await _ensure_tenant_id(db, current_user)

    # 场景路由 + 灰度校验：未启用 → 抛 6008 由全局异常处理器响应
    router_svc = ScenarioRouter(db)
    resolved = await router_svc.resolve(
        tenant_id=tenant_id,
        scenario_code=body.scenario_code,
        model_tier=body.model_tier,
    )

    # 会话持久化：建/复用 ai_session 行
    session_svc = SessionService(db)
    parsed_session_id: uuid.UUID | None = None
    if body.session_id:
        try:
            parsed_session_id = uuid.UUID(body.session_id)
        except ValueError:
            parsed_session_id = None

    ai_session = await session_svc.open(
        tenant_id=tenant_id,
        user_id=current_user.id,
        session_id=parsed_session_id,
        query=body.query,
        scenario_code=resolved.scenario_code,
        model_tier=resolved.model_tier,
    )
    session_id_out = str(ai_session.id)
    # 提交本次 open 写入，下面流里再单独提交 conversation_id 回填
    await db.commit()

    # 审计：记录场景 + 模型档位 + 会话信息
    try:
        audit_repo = SQLAlchemyAuditRepository(db)
        audit_svc = AuditService(audit_repo)
        client_ip = request.client.host if request.client else None
        await audit_svc.create_audit_log(
            AuditLogCreate(
                user_id=current_user.id,
                tenant_id=tenant_id,
                action=AUDIT_AI_CHAT_QUERY,
                module="ai",
                ip_address=client_ip,
                status="SUCCESS",
                details={
                    "query": body.query[:200],
                    "scenario_code": resolved.scenario_code,
                    "model_tier": resolved.model_tier,
                    "workflow_version": resolved.workflow_version,
                    "conversation_id": body.conversation_id,
                    "session_id": session_id_out,
                },
            )
        )
    except Exception:
        logger.warning("AI 查询审计日志写入失败", exc_info=True)

    # 用户密级：superadmin 强制最高（看所有档案）；其他用户走 user.secret_level（缺省 0）
    user_secret_level = (
        4
        if getattr(current_user, "is_superadmin", False)
        else int(getattr(current_user, "secret_level", 0) or 0)
    )

    # ── 后端检索（chat 入口先跑一遍，把 citations 注入到 SSE，不再依赖 Dify retriever） ──
    retrieval_svc = RetrievalService(db)
    filt = RetrieveFilter(
        tenant_id=tenant_id,
        secret_level=user_secret_level,
        user_id=current_user.id,
    )
    # 同时跑 rules + meta，两类引用合并。引用是"锦上添花"，ES 不可用时容忍降级为空，
    # 让聊天仍能流式；真正的故障提示由 dispatch_text → LLM 那条主链路给出，不在此重复报错。
    try:
        rule_hits = await retrieval_svc.retrieve(
            query=body.query, kb_type="rules", top_k=3, filt=filt
        )
        meta_hits = await retrieval_svc.retrieve(
            query=body.query, kb_type="meta", top_k=3, filt=filt
        )
    except RetrievalUnavailableError:
        logger.warning("chat 引用检索：ES 不可用，本轮引用降级为空")
        rule_hits, meta_hits = [], []
    all_hits = (rule_hits + meta_hits)[:6]
    citations_payload = [
        {
            "chunk_id": c.chunk_id,
            "source_type": c.source_type,
            "source_id": c.source_id,
            "title": c.title,
            "snippet": c.snippet,
            "score": c.score,
            "secret_level": c.secret_level,
            "tenant_id": c.tenant_id,
            "extra": c.extra,
        }
        for c in all_hits
    ]

    async def event_stream():
        # 首条：会话元信息
        meta = {
            "event": "scenario_resolved",
            "scenario_code": resolved.scenario_code,
            "model_tier": resolved.model_tier,
            "workflow_version": resolved.workflow_version,
            "gate": resolved.gate,
            "session_id": session_id_out,
            "citations_count": len(citations_payload),
        }
        yield f"data: {json.dumps(meta, ensure_ascii=False)}\n\n"

        # 第二条：后端命中引用（前端 chip 行直接消费此事件）
        if citations_payload:
            yield (
                "data: "
                + json.dumps(
                    {"event": "citations", "citations": citations_payload},
                    ensure_ascii=False,
                )
                + "\n\n"
            )

        # ── Dify 未配置时走本地兜底（仅当 API Key 为空时；正常演示不会进） ──
        if not (settings.DIFY_API_KEY or resolved.dify_api_key):
            logger.warning("DIFY_API_KEY 为空，chat 走本地 answer_synth 降级")
            answer = synthesize_answer(query=body.query, chunks=all_hits)
            yield (
                "data: "
                + json.dumps(
                    {"event": "message", "answer": answer, "conversation_id": ""},
                    ensure_ascii=False,
                )
                + "\n\n"
            )
            yield (
                "data: "
                + json.dumps(
                    {"event": "message_end", "conversation_id": "", "metadata": {}},
                    ensure_ascii=False,
                )
                + "\n\n"
            )
            try:
                await session_svc.increment_messages(session=ai_session)
                await db.commit()
            except Exception:
                logger.warning("ai_session 计数失败", exc_info=True)
            return

        captured_conv_id: str | None = None
        user_token = sign_user_token(
            user_id=user_id,
            tenant_id=str(tenant_id),
            secret_level=user_secret_level,
            scenario_code=resolved.scenario_code,
        )

        # A' 方案：所有场景统一走主 Chatflow（archive-agent），它内部 Classifier 节点会判断意图
        # 并通过 HTTP 节点回调后端 /v1/ai/internal/tool/dispatch 进入对应能力。
        # 前端 scenario_code 作为 scenario_hint 透传，若非空则跳过主 Chatflow 自己的分类。
        master_key = settings.DIFY_MASTER_API_KEY or resolved.dify_api_key
        async for chunk in dify_service.stream_chat(
            query=body.query,
            user_id=user_id,
            conversation_id=body.conversation_id,
            scenario_code=resolved.scenario_code,
            model_tier=resolved.model_tier,
            api_key=master_key,
            # 主 Chatflow Start 节点只接受 4 个变量；其余字段后端自留
            inputs={
                "scenario_hint": resolved.scenario_code,
                "citations_json": json.dumps(citations_payload, ensure_ascii=False),
                "tenant_id": str(tenant_id),
                "user_token": user_token,
            },
        ):
            if captured_conv_id is None and "conversation_id" in chunk:
                try:
                    line = chunk.split("\n", 1)[0]
                    if line.startswith("data:"):
                        evt = json.loads(line[5:].strip())
                        if evt.get("conversation_id"):
                            captured_conv_id = evt["conversation_id"]
                except (json.JSONDecodeError, IndexError, KeyError):
                    pass
            yield chunk

        if captured_conv_id:
            try:
                await session_svc.attach_dify_conversation(
                    session=ai_session, dify_conversation_id=captured_conv_id
                )
                await session_svc.increment_messages(session=ai_session)
                await db.commit()
            except Exception:
                logger.warning("ai_session conversation_id 回填失败", exc_info=True)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "X-Accel-Buffering": "no",
            "Cache-Control": "no-cache",
        },
    )


# ── AI 会话历史（替代前端 localStorage） ──────────────────────────────────


def _to_session_item(row: AISession) -> SessionItem:
    return SessionItem(
        id=str(row.id),
        title=row.title,
        last_scenario_code=row.last_scenario_code,
        last_model_tier=row.last_model_tier,
        message_count=row.message_count or 0,
        dify_conversation_id=row.dify_conversation_id,
        update_time=row.update_time.isoformat() if row.update_time else "",
        create_time=row.create_time.isoformat() if row.create_time else "",
    )


@router.get(
    "/sessions",
    summary="列出当前用户的 AI 会话",
    response_model=ResponseModel[SessionListResponse],
)
async def list_sessions(
    page: int = Query(default=1, ge=1),
    size: int = Query(default=30, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ResponseModel[SessionListResponse]:
    tenant_id = await _ensure_tenant_id(db, current_user)
    base = select(AISession).where(
        AISession.tenant_id == tenant_id,
        AISession.user_id == current_user.id,
        AISession.is_deleted.is_(False),
    )
    total = (
        await db.execute(select(func.count()).select_from(base.subquery()))
    ).scalar_one()
    stmt = (
        base.order_by(AISession.update_time.desc())
        .offset((page - 1) * size)
        .limit(size)
    )
    rows = (await db.execute(stmt)).scalars().all()
    return ResponseModel(
        data=SessionListResponse(total=total, items=[_to_session_item(r) for r in rows])
    )


@router.delete(
    "/sessions/{session_id}",
    summary="软删除一条 AI 会话",
    response_model=ResponseModel[None],
)
async def delete_session(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ResponseModel[None]:
    tenant_id = await _ensure_tenant_id(db, current_user)
    stmt = select(AISession).where(
        AISession.id == session_id,
        AISession.tenant_id == tenant_id,
        AISession.user_id == current_user.id,
        AISession.is_deleted.is_(False),
    )
    row = (await db.execute(stmt)).scalar_one_or_none()
    if row is None:
        raise BaseAPIException(
            code=ErrorCode.AI_PATCH_STATE_CONFLICT,
            message="会话不存在或无权限",
            status_code=404,
        )
    row.is_deleted = True
    await db.commit()
    return ResponseModel(data=None, message="已删除")
