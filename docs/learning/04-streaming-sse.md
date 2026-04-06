# 04 - 流式响应（SSE）：前后端设计

## 为什么需要流式输出

大模型生成回答是逐字输出的，完整回答可能需要 5-30 秒。  
如果等全部生成完再返回，用户会看到长时间白屏——体验极差。

**流式输出**让用户看到字一个个"打出来"，感知等待时间大幅缩短。

---

## SSE 协议（Server-Sent Events）

SSE 是 HTTP 标准协议，服务端向客户端单向推送数据。

**协议格式**（非常简单）：

```
HTTP/1.1 200 OK
Content-Type: text/event-stream    ← 关键 Content-Type
Cache-Control: no-cache

data: {"event":"message","answer":"你"}\n\n     ← 每条事件
data: {"event":"message","answer":"好"}\n\n
data: {"event":"message","answer":"！"}\n\n
data: {"event":"message_end","conversation_id":"abc"}\n\n
```

规则：
- 每行以 `data: ` 开头
- 每条事件以两个换行符 `\n\n` 结尾
- 连接保持打开直到显式关闭

---

## 后端：FastAPI StreamingResponse

```
用户请求 → FastAPI → Dify（流式）→ 原样转发给浏览器
```

关键代码（`modules/ai/api/routes.py`）：

```python
from fastapi.responses import StreamingResponse

async def event_stream():
    async for chunk in dify_service.stream_chat(query, user_id):
        yield chunk   # 每次 yield 就立刻发送给浏览器

return StreamingResponse(
    event_stream(),
    media_type="text/event-stream",   # 告诉浏览器这是 SSE
    headers={"X-Accel-Buffering": "no"}  # 告诉 Nginx 不要缓冲
)
```

**异步生成器**（`async def` + `yield`）是 Python 流式响应的核心：
- 每次 `yield` 一块数据，FastAPI 立即发送，不等待全部完成
- `async for` 逐块消费 Dify 的响应，避免阻塞

**`X-Accel-Buffering: no`** 这个 Header 很重要：  
如果部署时 Nginx 在前面做反向代理，Nginx 默认会缓冲响应，把流式变成批量。  
这个 Header 告诉 Nginx 关闭缓冲，数据实时透传。

---

## 前端：fetch + ReadableStream

不用 `EventSource` 的原因：`EventSource` 只支持 GET 请求，不能发 JSON Body，也不能加自定义 Authorization Header。

用 `fetch` + `ReadableStream` 替代（`api/ai.ts`）：

```typescript
// 1. 发起请求（带认证 Header）
const response = await fetch("/api/v1/ai/chat", {
  method: "POST",
  headers: { "Authorization": `Bearer ${token}` },
  body: JSON.stringify({ query }),
})

// 2. 获取流读取器
const reader = response.body.getReader()
const decoder = new TextDecoder()
let buffer = ""

while (true) {
  const { done, value } = await reader.read()  // 阻塞等待下一块数据
  if (done) break

  buffer += decoder.decode(value, { stream: true })  // 字节 → 字符串

  // 按行分割，解析 SSE
  const lines = buffer.split("\n")
  buffer = lines.pop()  // 最后一行可能不完整，留着等下一块

  for (const line of lines) {
    if (!line.startsWith("data:")) continue
    const chunk = JSON.parse(line.slice(5))
    // 拿到 chunk.answer，追加到消息气泡
  }
}
```

---

## @nlux 适配器模式

@nlux 不关心你用什么后端，只要实现 `ChatAdapter` 接口：

```typescript
const chatAdapter: ChatAdapter = {
  streamText: async (message, observer) => {
    // observer 是 @nlux 提供的"观察者"接口
    for await (const chunk of streamChat(message)) {
      observer.next(chunk.answer)   // 每块文字推给 @nlux
    }
    observer.complete()            // 结束
  }
}
```

@nlux 拿到数据后自动处理：
- 打字机动画效果
- Markdown 渲染（代码块、表格、列表）
- 滚动到最新消息
- 错误状态展示

---

## 数据流全链路

```
用户点击发送
    ↓
@nlux 调用 chatAdapter.streamText()
    ↓
api/ai.ts: fetch POST /api/v1/ai/chat（带 JWT）
    ↓
FastAPI: 验证 JWT → 写审计日志 → 调用 dify_service.stream_chat()
    ↓
Dify HTTP API（流式）
    ↓
Ollama qwen2.5:7b（逐 token 生成）
    ↓
Dify → FastAPI SSE → fetch ReadableStream → observer.next()
    ↓
@nlux 接收到文字 → 渲染到气泡（打字机效果）
    ↓
用户看到答案逐字出现
```

---

## 多轮对话：conversation_id

Dify 支持多轮对话，通过 `conversation_id` 关联上下文：

```
第1轮：发送问题，Dify 返回 conversation_id = "abc-123"
第2轮：发送问题 + conversation_id = "abc-123"，Dify 记得第1轮说了什么
```

`RagChatPanel.vue` 在 `message_end` 事件里保存 `conversation_id`：

```typescript
if (chunk.event === "message_end") {
  conversationId.value = chunk.conversation_id  // 保存供下一轮使用
}
```

---

## 启动后的操作步骤

1. `docker-compose up -d` 启动所有服务
2. 按 `03-ollama-and-dify.md` 拉取模型、配置 Dify、创建知识库、获取 API Key
3. 将 API Key 填入 `backend/.env` 的 `DIFY_API_KEY`
4. 重启后端：`python app/main.py`
5. 启动前端：`pnpm dev`
6. 访问仪表盘，点击"档案智能问答"面板开始对话
