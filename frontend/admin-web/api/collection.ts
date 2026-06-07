/**
 * 归档采集模块 API 层
 * 覆盖：批量导入五步流程 + 任务管理 + 映射模板
 */
import { service as http } from "@/utils/axios/service";

interface ApiResponse<T> {
  code: number;
  message: string;
  data: T;
}

// ─── 类型定义 ─────────────────────────────────────────────────────────────────

export interface ColumnMapping {
  source_col: string;
  target_field: string | null;
}

export interface UploadResponse {
  task_id: string;
  columns: string[];
  preview_rows: Record<string, string>[];
  auto_mappings: ColumnMapping[];
}

export interface DryRunRow {
  row: number;
  status: "ok" | "warning" | "error";
  message?: string;
  data?: Record<string, unknown>;
}

export interface DryRunResponse {
  task_id: string;
  total: number;
  ok: number;
  warning: number;
  error: number;
  rows: DryRunRow[];
}

export interface ImportTask {
  id: string;
  category_id: string;
  fonds_id: string;
  catalog_id: string;
  operator_id: string;
  status: "pending" | "running" | "done" | "failed";
  original_filename?: string;
  total: number;
  success: number;
  failed: number;
  skipped: number;
  started_at?: string;
  finished_at?: string;
  create_time: string;
}

export interface MappingTemplate {
  id: string;
  category_id: string;
  name: string;
  mappings: ColumnMapping[];
  is_default: boolean;
}

// ─── API ─────────────────────────────────────────────────────────────────────

export const ImportAPI = {
  /** 第1步：上传文件 */
  upload: (file: File, category_id: string, fonds_id: string, catalog_id: string) => {
    const form = new FormData();
    form.append("file", file);
    form.append("category_id", category_id);
    form.append("fonds_id", fonds_id);
    form.append("catalog_id", catalog_id);
    return http.post<ApiResponse<UploadResponse>, ApiResponse<UploadResponse>>("/archive/import/upload", form, {
      headers: { "Content-Type": "multipart/form-data" },
    });
  },

  /** 第2步：保存字段映射 */
  saveMapping: (
    task_id: string,
    mappings: ColumnMapping[],
    save_as_template?: boolean,
    template_name?: string,
  ) =>
    http.post<ApiResponse<null>, ApiResponse<null>>("/archive/import/mapping", {
      task_id,
      mappings,
      save_as_template: save_as_template ?? false,
      template_name,
    }),

  /** 第3步：预检 */
  dryRun: (task_id: string) =>
    http.post<ApiResponse<DryRunResponse>, ApiResponse<DryRunResponse>>("/archive/import/dry-run", { task_id }),

  /** 第4步：触发异步导入 */
  execute: (task_id: string) =>
    http.post<ApiResponse<{ celery_task_id: string }>, ApiResponse<{ celery_task_id: string }>>("/archive/import/execute", { task_id }),

  /** 任务列表 */
  listTasks: () => http.get<ApiResponse<ImportTask[]>, ApiResponse<ImportTask[]>>("/archive/import/tasks"),

  /** 任务详情 */
  getTask: (id: string) => http.get<ApiResponse<ImportTask>, ApiResponse<ImportTask>>(`/archive/import/tasks/${id}`),

  /** 失败报表预签名 URL */
  getReport: (id: string) =>
    http.get<ApiResponse<{ url: string }>, ApiResponse<{ url: string }>>(`/archive/import/tasks/${id}/report`),

  /** 映射模板列表 */
  listTemplates: (category_id?: string) =>
    http.get<ApiResponse<MappingTemplate[]>, ApiResponse<MappingTemplate[]>>("/archive/import/mapping-templates", {
      params: category_id ? { category_id } : {},
    }),

  /** 删除映射模板 */
  removeTemplate: (id: string) =>
    http.delete<ApiResponse<null>, ApiResponse<null>>(`/archive/import/mapping-templates/${id}`),
};

// ─── 归档移交 / 接收登记 / 收集台账 ───────────────────────────────────────────

export type TransferStatus = "draft" | "submitted" | "received" | "accepted" | "returned";

export interface TransferPlan {
  id: string;
  year: number;
  source_unit: string;
  source_org_id?: string | null;
  fonds_id: string;
  category_id: string;
  planned_count: number;
  due_date?: string | null;
  status: string;
  notes?: string | null;
  create_time: string;
}

export interface TransferPlanCreate {
  year: number;
  source_unit: string;
  fonds_id: string;
  category_id: string;
  planned_count?: number;
  due_date?: string | null;
  notes?: string | null;
}

export interface TransferEntryIn {
  TM: string;
  RZZ?: string | null;
  ND?: number | null;
  WJRQ?: string | null;
  YS?: number | null;
  MJ?: string | null;
  BGQX?: string | null;
  ext_fields?: Record<string, unknown> | null;
}

export interface TransferEntryOut extends TransferEntryIn {
  id: string;
  row_no: number;
  precheck_status: string;
  precheck_issues?: string[] | null;
  staging_id?: string | null;
}

export interface TransferBatch {
  id: string;
  transfer_no: string;
  plan_id?: string | null;
  source_unit: string;
  fonds_id: string;
  category_id: string;
  catalog_id?: string | null;
  year: number;
  handover_person: string;
  handover_date?: string | null;
  expected_count: number;
  status: TransferStatus;
  submitted_at?: string | null;
  received_at?: string | null;
  accepted_at?: string | null;
  handler_id?: string | null;
  precheck_score?: number | null;
  precheck_passed?: boolean | null;
  precheck_detail?: PrecheckDetail | null;
  return_reason?: string | null;
  notes?: string | null;
  create_time: string;
}

export interface TransferBatchDetail extends TransferBatch {
  entries: TransferEntryOut[];
}

export interface TransferBatchCreate {
  source_unit: string;
  fonds_id: string;
  category_id: string;
  catalog_id?: string | null;
  year: number;
  handover_person: string;
  handover_date?: string | null;
  plan_id?: string | null;
  notes?: string | null;
  entries: TransferEntryIn[];
}

export interface PrecheckDimension {
  key: string;
  label: string;
  score: number;
  weight: number;
  issues: string[];
}

export interface PrecheckDetail {
  score: number;
  passed: boolean;
  threshold: number;
  total: number;
  ok: number;
  warning: number;
  error: number;
  dimensions: PrecheckDimension[];
}

export interface PrecheckEntryResult {
  row_no: number;
  status: "ok" | "warning" | "error";
  issues: string[];
}

export interface PrecheckResponse extends PrecheckDetail {
  entries: PrecheckEntryResult[];
}

export interface LedgerRow {
  year: number;
  source_unit: string;
  fonds_id?: string | null;
  category_id?: string | null;
  planned_count: number;
  accepted_count: number;
  submitted_count: number;
  batch_total: number;
  completion_rate: number;
  overdue: boolean;
  due_date?: string | null;
}

export interface LedgerSummary {
  year?: number | null;
  total_planned: number;
  total_accepted: number;
  total_submitted: number;
  overall_completion_rate: number;
  overdue_units: number;
  rows: LedgerRow[];
}

const BASE = "/collection/transfer";

export const TransferAPI = {
  // 归档计划
  listPlans: (year?: number) =>
    http.get<ApiResponse<TransferPlan[]>, ApiResponse<TransferPlan[]>>(`${BASE}/plans`, {
      params: year ? { year } : {},
    }),
  createPlan: (body: TransferPlanCreate) =>
    http.post<ApiResponse<TransferPlan>, ApiResponse<TransferPlan>>(`${BASE}/plans`, body),
  updatePlan: (id: string, body: Partial<TransferPlanCreate> & { status?: string }) =>
    http.put<ApiResponse<TransferPlan>, ApiResponse<TransferPlan>>(`${BASE}/plans/${id}`, body),

  // 移交单
  listBatches: (params?: { status?: TransferStatus; year?: number }) =>
    http.get<ApiResponse<TransferBatch[]>, ApiResponse<TransferBatch[]>>(`${BASE}/batches`, {
      params: params ?? {},
    }),
  createBatch: (body: TransferBatchCreate) =>
    http.post<ApiResponse<TransferBatch>, ApiResponse<TransferBatch>>(`${BASE}/batches`, body),
  getBatch: (id: string) =>
    http.get<ApiResponse<TransferBatchDetail>, ApiResponse<TransferBatchDetail>>(`${BASE}/batches/${id}`),
  replaceEntries: (id: string, entries: TransferEntryIn[]) =>
    http.put<ApiResponse<TransferBatch>, ApiResponse<TransferBatch>>(`${BASE}/batches/${id}/entries`, { entries }),
  submitBatch: (id: string) =>
    http.post<ApiResponse<TransferBatch>, ApiResponse<TransferBatch>>(`${BASE}/batches/${id}/submit`, {}),
  previewPrecheck: (id: string) =>
    http.post<ApiResponse<PrecheckResponse>, ApiResponse<PrecheckResponse>>(`${BASE}/batches/${id}/precheck-preview`, {}),

  // 接收登记
  receivePrecheck: (id: string) =>
    http.post<ApiResponse<PrecheckResponse>, ApiResponse<PrecheckResponse>>(`${BASE}/receive/${id}/precheck`, {}),
  accept: (id: string, body: { catalog_id?: string | null; force?: boolean }) =>
    http.post<ApiResponse<TransferBatch>, ApiResponse<TransferBatch>>(`${BASE}/receive/${id}/accept`, body),
  returnBatch: (id: string, return_reason: string) =>
    http.post<ApiResponse<TransferBatch>, ApiResponse<TransferBatch>>(`${BASE}/receive/${id}/return`, { return_reason }),

  // 收集台账
  ledger: (year?: number) =>
    http.get<ApiResponse<LedgerSummary>, ApiResponse<LedgerSummary>>(`${BASE}/ledger`, {
      params: year ? { year } : {},
    }),
};
