/**
 * 智能著录 API（AI Cataloging）
 */
import { service as http } from "@/utils/axios/service";
import type { ArchiveCreate } from "@/api/repository";

interface ApiResponse<T> {
  code: number;
  data: T;
  message: string;
}

export interface CatalogCandidate {
  id: string;
  doc_source: "staging" | "formal";
  DH?: string;
  TM: string;
  QZH: string;
  ND?: number;
  category_id?: string;
  filled: number;
  total: number;
  status: "empty" | "missing" | "complete";
  attachment_count: number;
}

export interface FieldSuggestion {
  name: string;
  label: string;
  type: string;
  required: boolean;
  options: string[];
  current: string;
  suggested: string;
  confidence: number;
  evidence: string;
  similarity: number | null;
  kind: "none" | "fill" | "correct" | "keep";
  preselect: boolean;
  changed: boolean;
}

export interface SuggestResult {
  ok: boolean;
  reason?: string;
  message?: string;
  threshold?: number;
  chars?: number;
  full_text?: string;
  suggested_dh?: string;
  archive?: { id: string; DH?: string; TM: string; doc_source: string };
  suggestions?: FieldSuggestion[];
}

export const CatalogAPI = {
  candidates: (params?: { doc_source?: string; only_issues?: boolean; skip?: number; limit?: number }) =>
    http.get<ApiResponse<{ total: number; items: CatalogCandidate[] }>, ApiResponse<{ total: number; items: CatalogCandidate[] }>>(
      "/ai/catalog/candidates",
      { params },
    ),

  threshold: () =>
    http.get<ApiResponse<{ threshold: number }>, ApiResponse<{ threshold: number }>>("/ai/catalog/threshold"),

  suggest: (archiveId: string, doc_source: string) =>
    http.post<ApiResponse<SuggestResult>, ApiResponse<SuggestResult>>(
      `/ai/catalog/suggest/${archiveId}`,
      { doc_source },
    ),

  apply: (archiveId: string, doc_source: string, adopted: Record<string, string>) =>
    http.post<ApiResponse<{ ok: boolean; changed?: number; reason?: string }>, ApiResponse<{ ok: boolean; changed?: number; reason?: string }>>(
      `/ai/catalog/apply/${archiveId}`,
      { doc_source, adopted },
    ),

  /** 自动录入：上传 PDF/OFD + 门类 → OCR + 抽取 → 建议（multipart） */
  extract: (file: File, categoryId: string) => {
    const fd = new FormData();
    fd.append("file", file);
    fd.append("category_id", categoryId);
    return http.post<ApiResponse<SuggestResult>, ApiResponse<SuggestResult>>(
      "/ai/catalog/extract",
      fd,
      { headers: { "Content-Type": "multipart/form-data" }, timeout: 600000 },
    );
  },

  /** 自动录入：确认后新增入暂存库（带原文 PDF + 全文一起入库） */
  ingest: (file: File, payload: ArchiveCreate & { full_text?: string }) => {
    const fd = new FormData();
    fd.append("file", file);
    fd.append("payload", JSON.stringify(payload));
    return http.post<ApiResponse<{ id: string; DH?: string; TM: string }>, ApiResponse<{ id: string; DH?: string; TM: string }>>(
      "/ai/catalog/ingest",
      fd,
      { headers: { "Content-Type": "multipart/form-data" } },
    );
  },
};
