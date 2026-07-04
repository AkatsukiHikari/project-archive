"""
Dify API 调用服务

负责与 Dify 本地服务通信，处理：
- 流式聊天（SSE）
- 非流式聊天
- 会话管理

学习笔记：
  Dify 的聊天 API 遵循 SSE（Server-Sent Events）协议。
  SSE 是一种服务端向客户端单向推送数据的技术，每个事件格式为：
    data: {"event": "message", "answer": "你好", ...}\n\n
  我们把 Dify 返回的 SSE 流原样转发给前端，这样用户就能看到字逐渐出现的效果。
"""

import json
import logging
from typing import AsyncGenerator

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

# Dify 流式聊天端点
_DIFY_CHAT_URL = f"{settings.DIFY_BASE_URL}/chat-messages"


class DifyService:
    """
    封装对 Dify API 的调用。

    为什么用 httpx 而不是 requests？
    因为我们的 FastAPI 应用是异步的（async/await），
    requests 是同步库，在异步上下文中使用会阻塞事件循环。
    httpx 提供了异步版本，完全兼容 async/await。
    """

    def __init__(self) -> None:
        # 创建异步 HTTP 客户端，设置较长超时（大模型生成可能需要较长时间）
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(connect=10.0, read=120.0, write=10.0, pool=10.0)
        )

    async def stream_chat(
        self,
        query: str,
        user_id: str,
        conversation_id: str | None = None,
        scenario_code: str = "qa",
        model_tier: str | None = None,
        api_key: str | None = None,
        inputs: dict | None = None,
    ) -> AsyncGenerator[str, None]:
        """
        调用 Dify 流式聊天 API，返回 SSE 事件流。

        Args:
            query: 用户问题
            user_id: 当前用户ID（用于 Dify 的用户隔离）
            conversation_id: 多轮对话的会话ID，首次为 None
            scenario_code: 当前会话所属能力，注入到 Dify ``inputs``，主 Chatflow 路由用
            model_tier: 用户选择的模型档位（快/准/思考），注入到 Dify ``inputs``
            api_key: 覆盖默认 DIFY_API_KEY（不同 App 可能有不同 key；为空则用全局）
            inputs: 额外注入到 Dify ``inputs`` 的字段（context_archive_ids 等）

        Yields:
            SSE 格式的字符串，如 'data: {"event":"message","answer":"你好"}\\n\\n'
        """
        effective_key = api_key or settings.DIFY_API_KEY
        if not effective_key:
            yield 'data: {"event":"error","message":"AI服务未配置，请联系管理员设置 DIFY_API_KEY"}\n\n'
            return

        merged_inputs: dict = {"scenario_code": scenario_code}
        if model_tier:
            merged_inputs["model_tier"] = model_tier
        if inputs:
            merged_inputs.update(inputs)

        payload: dict = {
            "query": query,
            "user": user_id,
            "response_mode": "streaming",  # 流式模式
            "inputs": merged_inputs,
        }
        if conversation_id:
            payload["conversation_id"] = conversation_id

        headers = {
            "Authorization": f"Bearer {effective_key}",
            "Content-Type": "application/json",
        }

        try:
            # stream=True 表示使用流式 HTTP 响应，不等待全部内容再返回
            for attempt in (1, 2):
                async with self._client.stream(
                    "POST",
                    _DIFY_CHAT_URL,
                    json=payload,
                    headers=headers,
                ) as resp:
                    # 旧会话指向的应用已重建 → Dify 404，去掉 conversation_id 开新会话重试一次
                    if (
                        resp.status_code == 404
                        and "conversation_id" in payload
                        and attempt == 1
                    ):
                        payload.pop("conversation_id")
                        logger.warning(
                            "Dify 会话不存在（应用可能已重建），自动开新会话"
                        )
                        continue
                    if resp.status_code != 200:
                        error_body = await resp.aread()
                        logger.error(
                            "Dify API 错误 %d: %s", resp.status_code, error_body
                        )
                        yield f'data: {{"event":"error","message":"AI服务暂时不可用（{resp.status_code}）"}}\n\n'
                        return

                    # 逐行读取 SSE 事件
                    async for line in resp.aiter_lines():
                        if not line:
                            continue  # 跳过空行（SSE 事件分隔符）

                        # 原样转发给前端，保持 SSE 格式
                        yield f"{line}\n\n"

                        # 检测到结束事件时停止
                        if line.startswith("data:"):
                            try:
                                event_data = json.loads(line[5:].strip())
                                if event_data.get("event") in ("message_end", "error"):
                                    break
                            except json.JSONDecodeError:
                                pass
                    return

        except httpx.ConnectError:
            logger.error("无法连接到 Dify 服务: %s", _DIFY_CHAT_URL)
            yield 'data: {"event":"error","message":"AI服务连接失败，请确认 Dify 是否正常运行"}\n\n'
        except httpx.TimeoutException:
            logger.error("Dify 请求超时")
            yield 'data: {"event":"error","message":"AI响应超时，请稍后重试"}\n\n'
        except Exception as e:
            logger.exception("Dify 流式请求异常")
            yield f'data: {{"event":"error","message":"AI服务异常: {str(e)}"}}\n\n'

    async def upload_file(
        self, content: bytes, filename: str, user_id: str, api_key: str
    ) -> str:
        """上传文件到 Dify，返回 upload_file_id（供工作流 file 入参引用）。"""
        resp = await self._client.post(
            f"{settings.DIFY_BASE_URL}/files/upload",
            headers={"Authorization": f"Bearer {api_key}"},
            files={"file": (filename, content)},
            data={"user": user_id},
            timeout=httpx.Timeout(connect=10.0, read=120.0, write=120.0, pool=10.0),
        )
        resp.raise_for_status()
        return resp.json()["id"]

    async def run_workflow(
        self, inputs: dict, user_id: str, api_key: str, timeout_s: float = 600.0
    ) -> dict:
        """阻塞式跑工作流（OCR 这类耗时任务），返回 data.outputs。"""
        resp = await self._client.post(
            f"{settings.DIFY_BASE_URL}/workflows/run",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={"inputs": inputs, "response_mode": "blocking", "user": user_id},
            timeout=httpx.Timeout(connect=10.0, read=timeout_s, write=30.0, pool=10.0),
        )
        resp.raise_for_status()
        data = resp.json().get("data", {})
        if data.get("status") != "succeeded":
            raise RuntimeError(
                f"工作流失败 status={data.get('status')} error={data.get('error')}"
            )
        return data.get("outputs") or {}

    async def close(self) -> None:
        """关闭 HTTP 客户端，释放连接"""
        await self._client.aclose()


# 模块级单例，避免每次请求都创建新的 HTTP 客户端
dify_service = DifyService()
