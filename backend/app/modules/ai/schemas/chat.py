"""
AI 聊天相关 Pydantic Schema
"""

from typing import Literal, Optional

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """用户发送的聊天请求"""

    query: str = Field(..., min_length=1, max_length=2000, description="用户问题")
    conversation_id: Optional[str] = Field(
        default=None, description="会话ID（多轮对话时传入，首次为空）"
    )
    scenario_code: str = Field(
        default="qa",
        description="能力码：qa / search / summary / attach / catalog / fournat / draft / relate / kb_manage",
    )
    model_tier: Optional[Literal["快", "准", "思考"]] = Field(
        default=None, description="模型档位（缺省走场景默认）"
    )
    session_id: Optional[str] = Field(
        default=None,
        description="本地 AI 会话 ID（前端跨页跳转时携带，便于服务端建立 ai_session 关联）",
    )


class ChatSource(BaseModel):
    """引用来源片段"""

    content: str = Field(description="引用的档案文本片段")
    source: str = Field(description="来源文件名")
    score: float = Field(description="相似度分数")


class ChatResponse(BaseModel):
    """非流式聊天响应（仅用于 OpenAPI 文档展示，实际接口返回 SSE）"""

    answer: str = Field(description="大模型回答")
    conversation_id: str = Field(description="会话ID，供下次多轮对话使用")
    sources: list[ChatSource] = Field(default_factory=list, description="引用来源列表")


class ScenarioInfo(BaseModel):
    """单个场景配置（前端读取，决定 Tab 启用/灰度）"""

    code: str
    name: str
    description: str | None = None
    enabled: bool
    default_model_tier: str
    gate: str | None = None
    citation_required: bool = True


class ScenarioListResponse(BaseModel):
    """场景列表响应"""

    scenarios: list[ScenarioInfo]
    default_model_tier: str


class SessionItem(BaseModel):
    """单条 AI 会话索引"""

    id: str
    title: str
    last_scenario_code: Optional[str] = None
    last_model_tier: Optional[str] = None
    message_count: int = 0
    dify_conversation_id: Optional[str] = None
    update_time: str  # ISO 字符串
    create_time: str


class SessionListResponse(BaseModel):
    total: int
    items: list[SessionItem]
