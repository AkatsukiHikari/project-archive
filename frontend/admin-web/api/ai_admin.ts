/**
 * AI 管理端 API：patches / eval / audit
 *
 * P1 主要是读侧 + 占位。P2/P3 实装后保持本签名稳定。
 */
import { service as http } from "@/utils/axios/service";

interface ApiResponse<T> {
  code: number;
  data: T;
  message: string;
}

// ──────────────────────────────────────────────────────────────
// Patch
// ──────────────────────────────────────────────────────────────
export type PatchStatus = "pending" | "approved" | "rejected" | "applied" | "failed";
export type PatchGate = "auto" | "review" | "manual";

export interface PatchListItem {
  id: string;
  scenario_code: string;
  target_type: string;
  target_id: string | null;
  operation: string;
  status: PatchStatus;
  gate: PatchGate;
  confidence: number | null;
  workflow_version: string | null;
  reviewer_id: string | null;
  create_time: string;
  update_time: string;
}

export interface PatchDetail extends PatchListItem {
  payload: Record<string, unknown>;
  citations: Array<Record<string, unknown>>;
  reviewer_note: string | null;
  apply_error: string | null;
}

export interface PatchListResponse {
  total: number;
  items: PatchListItem[];
}

export function listPatches(params: {
  status?: string;
  scenario_code?: string;
  page?: number;
  size?: number;
} = {}): Promise<ApiResponse<PatchListResponse>> {
  return http.get<ApiResponse<PatchListResponse>, ApiResponse<PatchListResponse>>(
    "/ai/patches",
    { params },
  );
}

export function getPatch(patchId: string): Promise<ApiResponse<PatchDetail>> {
  return http.get<ApiResponse<PatchDetail>, ApiResponse<PatchDetail>>(
    `/ai/patches/${patchId}`,
  );
}

// ──────────────────────────────────────────────────────────────
// Eval
// ──────────────────────────────────────────────────────────────
export interface EvalRunListItem {
  id: string;
  scenario_code: string;
  workflow_version: string | null;
  model_tier: string | null;
  status: string;
  total: number | null;
  passed: number | null;
  metrics: Record<string, number>;
  threshold: Record<string, number>;
  blocked_upgrade: boolean;
  create_time: string;
  update_time: string;
}

export interface EvalRunListResponse {
  total: number;
  items: EvalRunListItem[];
}

export interface GoldenItem {
  id: string;
  scenario_code: string;
  input: Record<string, unknown>;
  expected: Record<string, unknown>;
  tags: string[];
  source: string;
  note: string | null;
  create_time: string;
}

export interface GoldenListResponse {
  total: number;
  items: GoldenItem[];
}

export function listEvalRuns(params: {
  scenario_code?: string;
  status?: string;
  page?: number;
  size?: number;
} = {}): Promise<ApiResponse<EvalRunListResponse>> {
  return http.get<ApiResponse<EvalRunListResponse>, ApiResponse<EvalRunListResponse>>(
    "/ai/eval/runs",
    { params },
  );
}

export function listGolden(params: {
  scenario_code?: string;
  source?: string;
  page?: number;
  size?: number;
} = {}): Promise<ApiResponse<GoldenListResponse>> {
  return http.get<ApiResponse<GoldenListResponse>, ApiResponse<GoldenListResponse>>(
    "/ai/eval/golden",
    { params },
  );
}
