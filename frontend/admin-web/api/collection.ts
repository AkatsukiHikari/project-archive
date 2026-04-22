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
    return http.post<ApiResponse<UploadResponse>>("/archive/import/upload", form, {
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
    http.post<ApiResponse<null>>("/archive/import/mapping", {
      task_id,
      mappings,
      save_as_template: save_as_template ?? false,
      template_name,
    }),

  /** 第3步：预检 */
  dryRun: (task_id: string) =>
    http.post<ApiResponse<DryRunResponse>>("/archive/import/dry-run", { task_id }),

  /** 第4步：触发异步导入 */
  execute: (task_id: string) =>
    http.post<ApiResponse<{ celery_task_id: string }>>("/archive/import/execute", { task_id }),

  /** 任务列表 */
  listTasks: () => http.get<ApiResponse<ImportTask[]>>("/archive/import/tasks"),

  /** 任务详情 */
  getTask: (id: string) => http.get<ApiResponse<ImportTask>>(`/archive/import/tasks/${id}`),

  /** 失败报表预签名 URL */
  getReport: (id: string) =>
    http.get<ApiResponse<{ url: string }>>(`/archive/import/tasks/${id}/report`),

  /** 映射模板列表 */
  listTemplates: (category_id?: string) =>
    http.get<ApiResponse<MappingTemplate[]>>("/archive/import/mapping-templates", {
      params: category_id ? { category_id } : {},
    }),

  /** 删除映射模板 */
  removeTemplate: (id: string) =>
    http.delete<ApiResponse<null>>(`/archive/import/mapping-templates/${id}`),
};
