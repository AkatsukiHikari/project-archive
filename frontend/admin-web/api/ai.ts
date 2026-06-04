/**
 * AI 聊天 API
 *
 * 学习笔记：SSE（Server-Sent Events）流式接收
 *
 * 传统 HTTP 请求：等服务器生成完整内容，一次性返回。
 * SSE 流式请求：服务器每生成一个字就推送过来，浏览器边收边显示。
 *
 * 实现方式：用原生 fetch + ReadableStream，比 EventSource 更灵活
 * （EventSource 不支持 POST 请求和自定义 Header）
 */

import { service as http } from "@/utils/axios/service";
import { useUserStore } from "@/stores/user";

interface ApiResponse<T> {
  code: number;
  data: T;
  message: string;
}

const API_BASE = "/ai";

export interface ChatChunk {
  event: string;
  answer?: string;
  conversation_id?: string;
  message?: string; // 错误消息
  scenario_code?: string;
  model_tier?: string;
  workflow_version?: string;
  gate?: string;
}

export type ModelTier = "快" | "准" | "思考";

export interface ScenarioInfo {
  code: string;
  name: string;
  description: string | null;
  enabled: boolean;
  default_model_tier: ModelTier;
  gate: string | null;
  citation_required: boolean;
}

export interface ScenarioListResponse {
  scenarios: ScenarioInfo[];
  default_model_tier: ModelTier;
}

export async function listScenarios(): Promise<ScenarioListResponse> {
  const res = await http.get<
    ApiResponse<ScenarioListResponse>,
    ApiResponse<ScenarioListResponse>
  >(`${API_BASE}/scenarios`);
  return res.data;
}

// ──────────────────────────────────────────────────────────────
// AI 会话历史
// ──────────────────────────────────────────────────────────────

export interface SessionItem {
  id: string;
  title: string;
  last_scenario_code: string | null;
  last_model_tier: string | null;
  message_count: number;
  dify_conversation_id: string | null;
  update_time: string;
  create_time: string;
}

export interface SessionListResponse {
  total: number;
  items: SessionItem[];
}

export async function listSessions(
  params: { page?: number; size?: number } = {},
): Promise<SessionListResponse> {
  const res = await http.get<ApiResponse<SessionListResponse>, ApiResponse<SessionListResponse>>(
    `${API_BASE}/sessions`,
    { params },
  );
  return res.data;
}

export async function deleteSession(sessionId: string): Promise<void> {
  await http.delete(`${API_BASE}/sessions/${sessionId}`);
}

// ──────────────────────────────────────────────────────────────
// 知识库管理
// ──────────────────────────────────────────────────────────────

export interface KBStatusItem {
  kb_type: "meta" | "rules" | "ocr";
  db_count: number;
  es_count: number | null;
  synced: boolean;
  last_synced_at: string | null;
  note: string | null;
}

export interface KBStatusResponse {
  items: KBStatusItem[];
}

export interface KBRebuildResponse {
  kb_type: string;
  scanned: number;
  synced: number;
  failed: number;
  duration_ms: number;
}

export async function getKBStatus(): Promise<KBStatusResponse> {
  const res = await http.get<ApiResponse<KBStatusResponse>, ApiResponse<KBStatusResponse>>(
    `${API_BASE}/kb/status`,
  );
  return res.data;
}

export async function rebuildKB(kb_type: "meta", batch_size = 200): Promise<KBRebuildResponse> {
  const res = await http.post<
    ApiResponse<KBRebuildResponse>,
    ApiResponse<KBRebuildResponse>
  >(`${API_BASE}/kb/rebuild`, { kb_type, batch_size });
  return res.data;
}

/**
 * 流式聊天：返回一个异步迭代器，调用方用 for await...of 逐块消费
 *
 * 用法：
 * ```ts
 * for await (const chunk of streamChat("查一下2023年的财务档案")) {
 *   if (chunk.answer) appendText(chunk.answer)
 * }
 * ```
 */
export async function* streamChat(
  query: string,
  conversationId?: string,
  signal?: AbortSignal,
): AsyncGenerator<ChatChunk> {
  const userStore = useUserStore();

  const response = await fetch(`${API_BASE}/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${userStore.token}`,
    },
    body: JSON.stringify({
      query,
      conversation_id: conversationId ?? null,
    }),
    signal,
  });

  if (!response.ok) {
    throw new Error(`AI 服务请求失败 (${response.status})`);
  }

  // ReadableStream：逐块读取响应体
  const reader = response.body?.getReader();
  if (!reader) throw new Error("无法获取响应流");

  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      // 将字节解码为字符串，追加到缓冲区
      buffer += decoder.decode(value, { stream: true });

      // 按行分割，解析 SSE 事件
      // SSE 格式：每个事件以 "data: " 开头，事件之间空行分隔
      const lines = buffer.split("\n");
      buffer = lines.pop() ?? ""; // 最后一行可能不完整，留在缓冲区

      for (const line of lines) {
        if (!line.startsWith("data:")) continue;
        const jsonStr = line.slice(5).trim();
        if (!jsonStr) continue;

        try {
          const chunk = JSON.parse(jsonStr) as ChatChunk;
          yield chunk;

          // 收到结束事件，停止读取
          if (chunk.event === "message_end" || chunk.event === "error") {
            return;
          }
        } catch {
          // 忽略无法解析的行
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}
