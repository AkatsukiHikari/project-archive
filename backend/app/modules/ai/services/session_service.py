"""
AI 会话持久化服务

每次 /chat 进来：
1. 若 ``session_id`` 来自前端、且属于当前租户/用户、未删除 → 复用并 +1 消息计数
2. 否则 → 新建一行 ``ai_session``（标题取 query 前 28 字）

流式响应结束（``message_end``）后回填 ``dify_conversation_id``，方便服务端日后拉历史。
"""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.ai.models.ai_session import AISession


def _make_title(query: str) -> str:
    snippet = (query or "").strip().replace("\n", " ")
    if not snippet:
        return "新对话"
    return snippet[:28] + ("…" if len(snippet) > 28 else "")


class SessionService:
    def __init__(self, db: AsyncSession):
        self._db = db

    async def open(
        self,
        *,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        session_id: uuid.UUID | None,
        query: str,
        scenario_code: str,
        model_tier: str,
    ) -> AISession:
        row: AISession | None = None
        if session_id is not None:
            stmt = select(AISession).where(
                AISession.id == session_id,
                AISession.tenant_id == tenant_id,
                AISession.user_id == user_id,
                AISession.is_deleted.is_(False),
            )
            row = (await self._db.execute(stmt)).scalar_one_or_none()

        if row is None:
            row = AISession(
                tenant_id=tenant_id,
                user_id=user_id,
                title=_make_title(query),
                last_scenario_code=scenario_code,
                last_model_tier=model_tier,
                message_count=1,
            )
            self._db.add(row)
        else:
            row.last_scenario_code = scenario_code
            row.last_model_tier = model_tier
            row.message_count = (row.message_count or 0) + 1

        await self._db.flush()
        return row

    async def attach_dify_conversation(
        self, *, session: AISession, dify_conversation_id: str
    ) -> None:
        if dify_conversation_id and session.dify_conversation_id != dify_conversation_id:
            session.dify_conversation_id = dify_conversation_id
            await self._db.flush()

    async def increment_messages(self, *, session: AISession) -> None:
        session.message_count = (session.message_count or 0) + 1
        await self._db.flush()
