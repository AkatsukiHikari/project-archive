/**
 * AI API（重构版）
 * - 问答 / 解读：SSE 流式（fetch + ReadableStream，支持 POST + 自定义 Header）
 * - OCR / 知识库：普通 http
 */
import { service as http } from "@/utils/axios/service";
import { useUserStore } from "@/stores/user";

interface ApiResponse<T> {
  code: number;
  data: T;
  message: string;
}

const API_BASE = "/api/v1/ai";

export interface ChatChunk {
  event: string;
  answer?: string;
  conversation_id?: string;
  message?: string;
}

export type ModelTier = "快" | "准" | "思考";

// ─── 流式：问答 / 解读 ─────────────────────────────────────────────────────────

async function* streamSSE(path: string, body: unknown, signal?: AbortSignal): AsyncGenerator<ChatChunk> {
  const userStore = useUserStore();
  const resp = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${userStore.token}` },
    body: JSON.stringify(body),
    signal,
  });
  if (!resp.ok) throw new Error(`AI 服务请求失败 (${resp.status})`);
  const reader = resp.body?.getReader();
  if (!reader) throw new Error("无法获取响应流");
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";
    for (const line of lines) {
      if (!line.startsWith("data:")) continue;
      const jsonStr = line.slice(5).trim();
      if (!jsonStr) continue;
      try {
        const chunk = JSON.parse(jsonStr) as ChatChunk;
        yield chunk;
        if (chunk.event === "message_end" || chunk.event === "error") return;
      } catch {
        // 忽略非 JSON 行（如 event: ping）
      }
    }
  }
}

/** 档案问答（ES 检索 + 知识库 + DeepSeek） */
export function streamChat(query: string, conversationId?: string, signal?: AbortSignal) {
  return streamSSE("/chat", { query, conversation_id: conversationId ?? null }, signal);
}

/** 解读单份档案（喂完整信息） */
export function streamInterpret(archiveId: string, signal?: AbortSignal) {
  return streamSSE("/interpret", { archive_id: archiveId }, signal);
}

// ─── OCR / 知识库 ─────────────────────────────────────────────────────────────

export interface OcrResult {
  ok: boolean;
  chars?: number;
  reason?: string;
}

export interface KBStatus {
  enabled: boolean;
  name?: string;
  dataset_id?: string;
  doc_count?: number;
  error?: string;
}

export interface OcrJob {
  id: string;
  archive_id: string;
  archive_dh?: string;
  archive_tm?: string;
  status: "pending" | "running" | "succeeded" | "failed";
  chars?: number;
  error?: string;
  create_time?: string;
  finished_at?: string;
}

export const AiAdminAPI = {
  /** 投递单条档案的 OCR 后台作业 */
  ocr: (archiveId: string) =>
    http.post<ApiResponse<OcrResult>, ApiResponse<OcrResult>>(`/ai/ocr/${archiveId}`),

  /** 批量投递（所有有 PDF 但未 OCR 的档案） */
  ocrBatch: () =>
    http.post<ApiResponse<{ queued: number }>, ApiResponse<{ queued: number }>>("/ai/ocr/batch"),

  /** OCR 作业列表（进度） */
  ocrJobs: (params?: { status?: string; skip?: number; limit?: number }) =>
    http.get<ApiResponse<{ total: number; items: OcrJob[] }>, ApiResponse<{ total: number; items: OcrJob[] }>>(
      "/ai/ocr/jobs",
      { params },
    ),

  /** 取档案存下的 OCR 全文 */
  ocrText: (archiveId: string) =>
    http.get<ApiResponse<{ full_text: string; chars: number }>, ApiResponse<{ full_text: string; chars: number }>>(
      `/ai/ocr/text/${archiveId}`,
    ),

  kbStatus: () =>
    http.get<ApiResponse<KBStatus>, ApiResponse<KBStatus>>("/ai/kb/status"),

  kbRebuild: () =>
    http.post<ApiResponse<{ synced: number }>, ApiResponse<{ synced: number }>>("/ai/kb/rebuild"),

  kbSyncOne: (archiveId: string) =>
    http.post<ApiResponse<{ ok: boolean; doc_id?: string }>, ApiResponse<{ ok: boolean; doc_id?: string }>>(
      `/ai/kb/sync/${archiveId}`,
    ),
};
