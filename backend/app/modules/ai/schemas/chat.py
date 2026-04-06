"""
AI 聊天相关 Pydantic Schema
"""

from pydantic import BaseModel, Field
from typing import Optional


class ChatRequest(BaseModel):
    """用户发送的聊天请求"""
    query: str = Field(..., min_length=1, max_length=2000, description="用户问题")
    conversation_id: Optional[str] = Field(
        default=None, description="会话ID（多轮对话时传入，首次为空）"
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
