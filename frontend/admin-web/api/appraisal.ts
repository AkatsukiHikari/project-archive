/**
 * 档案鉴定（开放鉴定）+ 工作台聚合 API 层
 * 流程：圈定预览 → 建计划分任务 → AI 预鉴定 → 人工核对 → 提交 → 审核 → 回写/台账
 */
import { service as http } from "@/utils/axios/service";

interface ApiResponse<T> {
  code: number;
  message: string;
  data: T;
}

// ─── 类型定义 ─────────────────────────────────────────────────────────────────

export type Kfzt = "开放" | "控制使用" | "延期开放" | "不开放";
export type TaskStatus = "pending" | "ai_running" | "ai_done" | "submitted" | "approved" | "rejected";
export type PlanStatus = "in_progress" | "completed";

export interface ScopeFondsGroup {
  fonds_id: string;
  QZH: string;
  fonds_name?: string;
  due_count: number;
}

export interface ScopePreview {
  total: number;
  groups: ScopeFondsGroup[];
}

export interface AppraisalTask {
  id: string;
  plan_id: string;
  fonds_id: string;
  QZH: string;
  fonds_name?: string;
  assignee_id: string;
  assignee_name?: string;
  status: TaskStatus;
  total: number;
  decided: number;
  reject_reason?: string;
  submitted_at?: string;
  reviewed_at?: string;
  create_time: string;
  plan_name?: string;
  plan_no?: string;
  ai_done?: number;
  pending?: number;
}

export interface AppraisalPlan {
  id: string;
  plan_no: string;
  name: string;
  appraisal_type: string;
  leader_id?: string;
  leader_name?: string;
  reviewer_id?: string;
  reviewer_name?: string;
  status: PlanStatus;
  description?: string;
  total_tasks: number;
  total_archives: number;
  finished_at?: string;
  create_time: string;
  tasks?: AppraisalTask[];
}

export interface AppraisalItem {
  id: string;
  task_id: string;
  archive_id: string;
  ND?: number;
  DH?: string;
  TM: string;
  QZH?: string;
  MJ?: string;
  BGQX?: string;
  due_basis?: string;
  ai_status: "pending" | "done" | "failed" | "skipped";
  ai_kfzt?: Kfzt;
  ai_reason?: string;
  ai_hit_words?: string[];
  ai_standard_code?: string;
  ai_confidence?: number;
  status: "pending" | "decided";
  final_kfzt?: Kfzt;
  final_reason?: string;
  final_standard_code?: string;
  decided_at?: string;
  plan_name?: string;
  plan_no?: string;
  reviewed_at?: string;
}

export interface Page<T> {
  total: number;
  items: T[];
}

export interface AppraisalStandard {
  id: string;
  code: string;
  title: string;
  content: string;
  target_kfzt: Kfzt;
  keywords?: string[];
  source?: string;
  is_enabled: boolean;
  sort_order: number;
  create_time: string;
}

export interface SensitiveWord {
  id: string;
  word: string;
  category?: string;
  suggest_kfzt: Kfzt;
  is_enabled: boolean;
  create_time: string;
}

export interface WorkbenchTodoItem {
  id: string;
  title: string;
  author?: string;
  time?: string;
  tag?: string;
  tag_color?: string;
  link: string;
}

export interface WorkbenchTab {
  key: string;
  label: string;
  count: number;
  danger: boolean;
  items: WorkbenchTodoItem[];
}

export interface WorkbenchOverview {
  kpi: {
    fonds_count: number;
    archive_total: number;
    month_new: number;
    todo_total: number;
  };
  tabs: WorkbenchTab[];
}

// ─── 鉴定流程 API ─────────────────────────────────────────────────────────────

export const AppraisalAPI = {
  /** 到期圈定预览（按全宗分组） */
  scopePreview: () =>
    http.get<ApiResponse<ScopePreview>, ApiResponse<ScopePreview>>("/appraisal/scope-preview"),

  /** 创建鉴定计划（含任务分配） */
  createPlan: (data: {
    name: string;
    reviewer_id: string;
    description?: string;
    tasks: { fonds_id: string; assignee_id: string }[];
  }) => http.post<ApiResponse<AppraisalPlan>, ApiResponse<AppraisalPlan>>("/appraisal/plans", data),

  listPlans: (params?: { status?: PlanStatus; skip?: number; limit?: number }) =>
    http.get<ApiResponse<Page<AppraisalPlan>>, ApiResponse<Page<AppraisalPlan>>>("/appraisal/plans", { params }),

  getPlan: (id: string) =>
    http.get<ApiResponse<AppraisalPlan>, ApiResponse<AppraisalPlan>>(`/appraisal/plans/${id}`),

  /** 我的任务（role=assignee 鉴定 / reviewer 审核） */
  listTasks: (params?: { role?: "assignee" | "reviewer"; status?: TaskStatus; skip?: number; limit?: number }) =>
    http.get<ApiResponse<Page<AppraisalTask>>, ApiResponse<Page<AppraisalTask>>>("/appraisal/tasks", { params }),

  getTask: (id: string) =>
    http.get<ApiResponse<AppraisalTask>, ApiResponse<AppraisalTask>>(`/appraisal/tasks/${id}`),

  listItems: (taskId: string, params?: {
    status?: "pending" | "decided";
    kfzt?: Kfzt;
    keyword?: string;
    skip?: number;
    limit?: number;
  }) =>
    http.get<ApiResponse<Page<AppraisalItem>>, ApiResponse<Page<AppraisalItem>>>(
      `/appraisal/tasks/${taskId}/items`, { params },
    ),

  /** AI 预鉴定（规则同步 + LLM 后台） */
  runAi: (taskId: string) =>
    http.post<ApiResponse<AppraisalTask>, ApiResponse<AppraisalTask>>(`/appraisal/tasks/${taskId}/ai-run`),

  /** 批量采纳 AI 建议 */
  adoptAi: (taskId: string) =>
    http.post<ApiResponse<{ adopted: number }>, ApiResponse<{ adopted: number }>>(`/appraisal/tasks/${taskId}/adopt-ai`),

  /** 单条人工结论 */
  decideItem: (itemId: string, data: { final_kfzt: Kfzt; final_reason?: string; final_standard_code?: string }) =>
    http.put<ApiResponse<AppraisalItem>, ApiResponse<AppraisalItem>>(`/appraisal/items/${itemId}/decide`, data),

  submitTask: (taskId: string) =>
    http.post<ApiResponse<AppraisalTask>, ApiResponse<AppraisalTask>>(`/appraisal/tasks/${taskId}/submit`),

  approveTask: (taskId: string) =>
    http.post<ApiResponse<AppraisalTask>, ApiResponse<AppraisalTask>>(`/appraisal/tasks/${taskId}/approve`),

  rejectTask: (taskId: string, reason: string) =>
    http.post<ApiResponse<AppraisalTask>, ApiResponse<AppraisalTask>>(`/appraisal/tasks/${taskId}/reject`, { reason }),

  /** 鉴定台账（审核通过明细） */
  listLedger: (params?: {
    qzh?: string;
    kfzt?: Kfzt;
    plan_id?: string;
    keyword?: string;
    skip?: number;
    limit?: number;
  }) =>
    http.get<ApiResponse<Page<AppraisalItem>>, ApiResponse<Page<AppraisalItem>>>("/appraisal/ledger", { params }),
};

// ─── 标准 / 敏感词 API ────────────────────────────────────────────────────────

export const AppraisalStandardAPI = {
  list: (enabled_only = false) =>
    http.get<ApiResponse<AppraisalStandard[]>, ApiResponse<AppraisalStandard[]>>("/appraisal/standards", {
      params: { enabled_only },
    }),
  create: (data: Partial<AppraisalStandard>) =>
    http.post<ApiResponse<AppraisalStandard>, ApiResponse<AppraisalStandard>>("/appraisal/standards", data),
  update: (id: string, data: Partial<AppraisalStandard>) =>
    http.put<ApiResponse<AppraisalStandard>, ApiResponse<AppraisalStandard>>(`/appraisal/standards/${id}`, data),
  remove: (id: string) => http.delete<ApiResponse<null>, ApiResponse<null>>(`/appraisal/standards/${id}`),

  listWords: (params?: { keyword?: string; skip?: number; limit?: number }) =>
    http.get<ApiResponse<Page<SensitiveWord>>, ApiResponse<Page<SensitiveWord>>>("/appraisal/words", { params }),
  createWord: (data: Partial<SensitiveWord>) =>
    http.post<ApiResponse<SensitiveWord>, ApiResponse<SensitiveWord>>("/appraisal/words", data),
  updateWord: (id: string, data: Partial<SensitiveWord>) =>
    http.put<ApiResponse<SensitiveWord>, ApiResponse<SensitiveWord>>(`/appraisal/words/${id}`, data),
  removeWord: (id: string) => http.delete<ApiResponse<null>, ApiResponse<null>>(`/appraisal/words/${id}`),
};

// ─── 工作台 API ───────────────────────────────────────────────────────────────

export const WorkbenchAPI = {
  overview: () =>
    http.get<ApiResponse<WorkbenchOverview>, ApiResponse<WorkbenchOverview>>("/workbench/overview"),
};
