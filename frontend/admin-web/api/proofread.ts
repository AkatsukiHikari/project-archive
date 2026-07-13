/**
 * 智能校对 API（批量条目-原文比对）
 */
import { service as http } from "@/utils/axios/service";

interface ApiResponse<T> {
  code: number;
  data: T;
  message: string;
}

/** 检索范围（与档案列表同一套过滤条件） */
export interface ProofreadQuery {
  fonds_id?: string;
  catalog_id?: string;
  category_id?: string;
  keyword?: string;
  TM?: string;
  RZZ?: string;
  DH?: string;
  ND_from?: number;
  ND_to?: number;
  page?: number;
  page_size?: number;
}

export type ProofreadDocSource = "all" | "staging" | "formal";

export type ProofreadVerdict =
  | "none"        // 有原文但从未校对
  | "no_pdf"      // 无 PDF 挂接，无法校对
  | "pending"     // 批次中待处理
  | "consistent"  // 一致
  | "flagged"     // 存疑
  | "resolved"    // 已整改
  | "no_text"     // 原文识别不出文字
  | "failed";     // 校对失败

export interface ProofreadIssue {
  name: string;
  label: string;
  kind: "fill" | "correct";
  current: string;
  suggested: string;
  confidence: number;
  evidence: string;
  similarity: number | null;
}

export interface ProofreadRecord {
  id: string;
  doc_source: "staging" | "formal";
  DH?: string;
  TM: string;
  QZH?: string;
  ND?: number;
  category_id?: string | null;
  /** 完整度：必录字段已填数 / 必录字段总数（与智能著录工作台同口径） */
  filled: number;
  total_required: number;
  has_pdf: boolean;
  verdict: ProofreadVerdict;
  issue_count: number;
  issues: ProofreadIssue[] | null;
  checked_at?: string | null;
}

export interface ProofreadBatch {
  id: string;
  scope_label?: string;
  doc_source: ProofreadDocSource;
  total: number;
  processed: number;
  consistent: number;
  flagged: number;
  no_text: number;
  failed: number;
  status: "running" | "done" | "failed" | "canceled";
  started_at?: string | null;
  finished_at?: string | null;
}

export interface ProofreadPreview {
  total: number;
  with_pdf: number;
  need_ocr: number;
  no_pdf: number;
}

export const ProofreadAPI = {
  preview: (doc_source: ProofreadDocSource, query: ProofreadQuery) =>
    http.post<ApiResponse<ProofreadPreview>, ApiResponse<ProofreadPreview>>(
      "/ai/proofread/preview",
      { doc_source, query },
    ),

  start: (doc_source: ProofreadDocSource, query: ProofreadQuery, scope_label: string, force: boolean) =>
    http.post<ApiResponse<{ ok: boolean; batch_id?: string; total?: number; reason?: string }>, ApiResponse<{ ok: boolean; batch_id?: string; total?: number; reason?: string }>>(
      "/ai/proofread/start",
      { doc_source, query, scope_label, force },
    ),

  batches: (params?: { skip?: number; limit?: number }) =>
    http.get<ApiResponse<{ total: number; items: ProofreadBatch[] }>, ApiResponse<{ total: number; items: ProofreadBatch[] }>>(
      "/ai/proofread/batches",
      { params },
    ),

  batch: (batchId: string) =>
    http.get<ApiResponse<ProofreadBatch & { ok?: boolean; reason?: string }>, ApiResponse<ProofreadBatch & { ok?: boolean; reason?: string }>>(
      `/ai/proofread/batches/${batchId}`,
    ),

  cancel: (batchId: string) =>
    http.post<ApiResponse<{ ok: boolean; reason?: string }>, ApiResponse<{ ok: boolean; reason?: string }>>(
      `/ai/proofread/batches/${batchId}/cancel`,
    ),

  records: (doc_source: ProofreadDocSource, query: ProofreadQuery, verdict?: string) =>
    http.post<ApiResponse<{ total: number; items: ProofreadRecord[] }>, ApiResponse<{ total: number; items: ProofreadRecord[] }>>(
      "/ai/proofread/records",
      { doc_source, query, verdict: verdict || null },
    ),

  resolve: (archiveId: string) =>
    http.post<ApiResponse<{ ok: boolean; reason?: string }>, ApiResponse<{ ok: boolean; reason?: string }>>(
      `/ai/proofread/resolve/${archiveId}`,
    ),
};
