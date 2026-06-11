/**
 * 四性检测 API：检测项目录 + 检测方案 + 检测运行
 */
import { service as http } from "@/utils/axios/service";

interface ApiResponse<T> {
  code: number;
  message: string;
  data: T;
}

export type Dimension = "authenticity" | "integrity" | "usability" | "safety";
export type ExecType = "rule" | "ai" | "manual";
export type CheckResult = "pass" | "warn" | "fail" | "skip" | "manual_pending";
export type Conclusion = "pass" | "warn" | "fail" | "pending";

export interface CheckItem {
  id: string;
  code: string;
  name: string;
  dimension: Dimension;
  exec_type: ExecType;
  standard_ref?: string | null;
  description?: string | null;
  carrier_type: string;
  default_weight: number;
  default_blocking: boolean;
  enabled: boolean;
}

export interface SchemeItem {
  id?: string;
  check_code: string;
  check_name?: string | null;
  dimension?: Dimension | null;
  exec_type?: ExecType | null;
  standard_ref?: string | null;
  enabled: boolean;
  weight?: number | null;
  is_blocking?: boolean | null;
  params?: Record<string, unknown> | null;
  sort_order?: number;
}

export interface Scheme {
  id: string;
  name: string;
  description?: string | null;
  carrier_type: string;
  is_default: boolean;
  version: number;
  status: string;
  create_time: string;
  item_count: number;
}

export interface SchemeDetail extends Scheme {
  items: SchemeItem[];
}

export interface SchemeCreate {
  name: string;
  description?: string | null;
  carrier_type?: string;
  is_default?: boolean;
  items: SchemeItem[];
}

export interface ResultItem {
  id: string;
  check_code: string;
  check_name: string;
  dimension: Dimension;
  exec_type: ExecType;
  result: CheckResult;
  score: number;
  weight: number;
  is_blocking: boolean;
  message?: string | null;
  evidence?: Record<string, unknown> | null;
  confidence?: number | null;
  standard_ref?: string | null;
  decided_by?: string | null;
}

export interface Run {
  id: string;
  target_id: string;
  target_label?: string | null;
  scheme_name?: string | null;
  scheme_version?: number | null;
  overall_score: number;
  dim_scores?: Record<string, number> | null;
  conclusion: Conclusion;
  status: string;
  total: number;
  passed: number;
  warned: number;
  failed: number;
  manual_pending: number;
  finished_at?: string | null;
  create_time: string;
}

export interface RunDetail extends Run {
  results: ResultItem[];
}

export interface Batch {
  id: string;
  batch_no: string;
  scope_type: string;
  scope_label?: string | null;
  scheme_name?: string | null;
  total: number;
  passed: number;
  warned: number;
  failed: number;
  pending: number;
  avg_score: number;
  dim_scores?: Record<string, number> | null;
  conclusion: Conclusion;
  status: string;
  finished_at?: string | null;
  create_time: string;
}

export interface BatchDetail extends Batch {
  runs: Run[];
}

const P = "/preservation";

export const PreservationAPI = {
  checkItems: () => http.get<ApiResponse<CheckItem[]>, ApiResponse<CheckItem[]>>(`${P}/check-items`),
  schemes: () => http.get<ApiResponse<Scheme[]>, ApiResponse<Scheme[]>>(`${P}/schemes`),
  createScheme: (body: SchemeCreate) => http.post<ApiResponse<Scheme>, ApiResponse<Scheme>>(`${P}/schemes`, body),
  getScheme: (id: string) => http.get<ApiResponse<SchemeDetail>, ApiResponse<SchemeDetail>>(`${P}/schemes/${id}`),
  updateScheme: (id: string, body: Partial<SchemeCreate>) => http.put<ApiResponse<Scheme>, ApiResponse<Scheme>>(`${P}/schemes/${id}`, body),
  setDefault: (id: string) => http.post<ApiResponse<Scheme>, ApiResponse<Scheme>>(`${P}/schemes/${id}/default`, {}),
  deleteScheme: (id: string) => http.delete<ApiResponse<null>, ApiResponse<null>>(`${P}/schemes/${id}`),
  batches: () => http.get<ApiResponse<Batch[]>, ApiResponse<Batch[]>>(`${P}/batches`),
  getBatch: (id: string) => http.get<ApiResponse<BatchDetail>, ApiResponse<BatchDetail>>(`${P}/batches/${id}`),
  runDetection: (body: { archive_id: string; scheme_id?: string }) => http.post<ApiResponse<Batch>, ApiResponse<Batch>>(`${P}/runs`, body),
  runBatch: (body: { scheme_id?: string; fonds_id?: string; catalog_id?: string; category_id?: string; ND?: number }) =>
    http.post<ApiResponse<Batch>, ApiResponse<Batch>>(`${P}/runs/batch`, body),
  getRun: (id: string) => http.get<ApiResponse<RunDetail>, ApiResponse<RunDetail>>(`${P}/runs/${id}`),
  decide: (runId: string, itemId: string, body: { result: string; message?: string }) =>
    http.post<ApiResponse<Run>, ApiResponse<Run>>(`${P}/runs/${runId}/results/${itemId}/decide`, body),
};
