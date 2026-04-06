"""
AI 聊天 API 路由

端点：
- POST /v1/ai/chat  — 流式聊天（SSE），供前端 @nlux/vue 消费

学习笔记：
  StreamingResponse 是 FastAPI 提供的流式响应类。
  它接受一个异步生成器，逐块将数据发送给客户端，不等待全部内容生成完毕。
  配合 media_type="text/event-stream" 就是标准的 SSE 协议。
"""

import logging

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.ai.schemas.chat import ChatRequest
from app.modules.ai.services.dify_service import dify_service
from app.modules.iam.api.dependencies import get_current_user
from app.modules.iam.models.user import User
from app.modules.audit.services.audit_service import AuditService
from app.modules.audit.repositories.audit_repository import SQLAlchemyAuditRepository
from app.modules.audit.schemas.audit_log import AuditLogCreate
from app.infra.db.session import get_db

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/chat",
    summary="档案智能问答（流式）",
    description="""
    与 AI 档案助手对话，基于已入库的档案知识库回答问题。

    **响应格式**：Server-Sent Events (SSE)

    每个事件格式（来自 Dify）：
    ```
    data: {"event": "message", "answer": "回答文字片段", "conversation_id": "xxx"}
    data: {"event": "message_end", "conversation_id": "xxx", "metadata": {...}}
    ```

    前端用 @nlux/vue 的 streamAdapter 自动处理，无需手动解析。
    """,
)
async def chat(
    request: Request,
    body: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """
    流式聊天端点。

    安全设计：
    1. get_current_user 确保只有登录用户才能访问
    2. user_id 从 JWT 中提取，不信任客户端传入
    3. 审计日志记录每次查询（问了什么、谁问的）
    """
    user_id = str(current_user.id)

    # 记录审计日志（异步，不阻塞响应）
    try:
        audit_repo = SQLAlchemyAuditRepository(db)
        audit_svc = AuditService(audit_repo)
        client_ip = request.client.host if request.client else None
        await audit_svc.create_audit_log(AuditLogCreate(
            user_id=current_user.id,
            tenant_id=current_user.tenant_id,
            action="ai_chat_query",
            module="ai",
            ip_address=client_ip,
            status="SUCCESS",
            details={"query": body.query[:200]},  # 只记录前200字
        ))
    except Exception:
        # 审计失败不应阻断正常对话
        logger.warning("AI 查询审计日志写入失败", exc_info=True)

    # 创建流式生成器
    async def event_stream():
        async for chunk in dify_service.stream_chat(
            query=body.query,
            user_id=user_id,
            conversation_id=body.conversation_id,
        ):
            yield chunk

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            # 关闭 nginx 缓冲，确保数据实时到达浏览器
            "X-Accel-Buffering": "no",
            "Cache-Control": "no-cache",
        },
    )
