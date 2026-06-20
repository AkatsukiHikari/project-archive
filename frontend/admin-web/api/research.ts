/**
 * 档案编研 API 层
 * 流程：项目立项 → 选材 → 成果编纂（类 Word 在线文档 + 成果档案库 + AI 起草）→ 提交 → 定稿 → 发布
 * 成果库为通用编研成果库，成果可独立于项目存在；每个成果有自己的引用档案库。
 */
import { service as http } from "@/utils/axios/service";

interface ApiResponse<T> {
  code: number;
  message: string;
  data: T;
}

// ─── 类型定义 ─────────────────────────────────────────────────────────────────

export type ResultType =
  | "大事记"
  | "组织沿革"
  | "专题汇编"
  | "基础数字汇编"
  | "参考资料"
  | "全宗指南";

export const RESULT_TYPES: ResultType[] = [
  "大事记",
  "组织沿革",
  "专题汇编",
  "基础数字汇编",
  "参考资料",
  "全宗指南",
];

export type ProjectStatus = "in_progress" | "completed";
export type ResultStatus = "draft" | "reviewing" | "finalized" | "published";

export interface ResearchProject {
  id: string;
  title: string;
  project_type: ResultType;
  editor_id?: string;
  editor_name?: string;
  reviewer_id?: string;
  reviewer_name?: string;
  members?: string[];
  start_date?: string;
  end_date?: string;
  purpose?: string;
  status: ProjectStatus;
  material_count: number;
  result_count: number;
  create_time: string;
}

export interface ProjectPayload {
  title: string;
  project_type: ResultType;
  editor_id?: string | null;
  reviewer_id?: string | null;
  members?: string[];
  start_date?: string | null;
  end_date?: string | null;
  purpose?: string | null;
  status?: ProjectStatus;
}

/** 档案快照（项目素材 / 成果档案库共用展示字段） */
export interface ArchiveSnapshot {
  id: string;
  archive_id: string;
  DH?: string;
  TM: string;
  RZZ?: string;
  ND?: number;
  WJRQ?: string;
  QZH?: string;
}

export type ResearchMaterial = ArchiveSnapshot;

export interface ResultArchive extends ArchiveSnapshot {
  sort_order: number;
}

/** 列表项（不含正文） */
export interface ResearchResultItem {
  id: string;
  project_id?: string;
  project_title?: string;
  title: string;
  result_type: ResultType;
  summary?: string;
  status: ResultStatus;
  archive_count: number;
  create_time: string;
}

/** 完整成果（含正文 HTML / 文档 JSON） */
export interface ResearchResult extends ResearchResultItem {
  content?: string;
  content_json?: Record<string, unknown> | null;
  author_id?: string;
  reviewer_id?: string;
  finalized_at?: string;
  published_at?: string;
}

export interface ResultPayload {
  project_id?: string | null;
  title: string;
  result_type: ResultType;
  summary?: string | null;
  content?: string | null;
  content_json?: Record<string, unknown> | null;
  template_id?: string | null;
}

export interface ResearchTemplate {
  id: string;
  name: string;
  result_type: ResultType;
  description?: string;
  content?: string;
  content_json?: Record<string, unknown> | null;
  is_builtin: boolean;
  sort_order: number;
  create_time: string;
}

export interface TemplatePayload {
  name: string;
  result_type: ResultType;
  description?: string | null;
  content?: string | null;
  content_json?: Record<string, unknown> | null;
  sort_order?: number;
}

export interface AiDraftResult {
  summary?: string;
  content: string;
}

export interface UploadResult {
  id: string;
  url: string;
  name: string;
  size: number;
  type: string;
}

export interface ResultPage {
  total: number;
  items: ResearchResultItem[];
}

export type ResultAction = "submit" | "finalize" | "publish" | "reopen";

// ─── 项目 API ─────────────────────────────────────────────────────────────────

export const ResearchProjectAPI = {
  list: (params?: { status?: ProjectStatus }) =>
    http.get<ApiResponse<ResearchProject[]>, ApiResponse<ResearchProject[]>>("/research/projects", { params }),

  get: (id: string) =>
    http.get<ApiResponse<ResearchProject>, ApiResponse<ResearchProject>>(`/research/projects/${id}`),

  create: (data: ProjectPayload) =>
    http.post<ApiResponse<ResearchProject>, ApiResponse<ResearchProject>>("/research/projects", data),

  update: (id: string, data: Partial<ProjectPayload>) =>
    http.put<ApiResponse<ResearchProject>, ApiResponse<ResearchProject>>(`/research/projects/${id}`, data),

  remove: (id: string) =>
    http.delete<ApiResponse<null>, ApiResponse<null>>(`/research/projects/${id}`),

  // ── 选材 ──
  listMaterials: (id: string) =>
    http.get<ApiResponse<ResearchMaterial[]>, ApiResponse<ResearchMaterial[]>>(`/research/projects/${id}/materials`),

  addMaterials: (id: string, archive_ids: string[]) =>
    http.post<ApiResponse<{ added: number }>, ApiResponse<{ added: number }>>(
      `/research/projects/${id}/materials`,
      { archive_ids },
    ),

  removeMaterial: (materialId: string) =>
    http.delete<ApiResponse<null>, ApiResponse<null>>(`/research/materials/${materialId}`),
};

// ─── 成果 API ─────────────────────────────────────────────────────────────────

export const ResearchResultAPI = {
  list: (params?: {
    result_type?: ResultType;
    status?: ResultStatus;
    project_id?: string;
    keyword?: string;
    skip?: number;
    limit?: number;
  }) =>
    http.get<ApiResponse<ResultPage>, ApiResponse<ResultPage>>("/research/results", { params }),

  get: (id: string) =>
    http.get<ApiResponse<ResearchResult>, ApiResponse<ResearchResult>>(`/research/results/${id}`),

  create: (data: ResultPayload) =>
    http.post<ApiResponse<ResearchResult>, ApiResponse<ResearchResult>>("/research/results", data),

  update: (id: string, data: Partial<ResultPayload>) =>
    http.put<ApiResponse<ResearchResult>, ApiResponse<ResearchResult>>(`/research/results/${id}`, data),

  remove: (id: string) =>
    http.delete<ApiResponse<null>, ApiResponse<null>>(`/research/results/${id}`),

  /** 状态流转：submit 提交审核 / finalize 定稿 / publish 发布 / reopen 撤回 */
  transition: (id: string, action: ResultAction) =>
    http.post<ApiResponse<ResearchResult>, ApiResponse<ResearchResult>>(`/research/results/${id}/${action}`),

  // ── 成果档案库 ──
  listArchives: (id: string) =>
    http.get<ApiResponse<ResultArchive[]>, ApiResponse<ResultArchive[]>>(`/research/results/${id}/archives`),

  addArchives: (id: string, payload: { archive_ids?: string[]; from_project?: boolean }) =>
    http.post<ApiResponse<{ added: number }>, ApiResponse<{ added: number }>>(
      `/research/results/${id}/archives`,
      payload,
    ),

  removeArchive: (raId: string) =>
    http.delete<ApiResponse<null>, ApiResponse<null>>(`/research/result-archives/${raId}`),

  /** 按成果档案库文件日期生成大事记表格 HTML（不走 AI） */
  chronicleTable: (id: string) =>
    http.post<ApiResponse<{ html: string }>, ApiResponse<{ html: string }>>(`/research/results/${id}/chronicle-table`),

  /** AI 依据成果档案库生成可插入文档的 HTML 草稿 */
  aiDraft: (data: { result_id: string; topic?: string }) =>
    http.post<ApiResponse<AiDraftResult>, ApiResponse<AiDraftResult>>("/research/ai-draft", data),
};

// ─── 模板 API ─────────────────────────────────────────────────────────────────

export const ResearchTemplateAPI = {
  list: (params?: { result_type?: ResultType }) =>
    http.get<ApiResponse<ResearchTemplate[]>, ApiResponse<ResearchTemplate[]>>("/research/templates", { params }),

  get: (id: string) =>
    http.get<ApiResponse<ResearchTemplate>, ApiResponse<ResearchTemplate>>(`/research/templates/${id}`),

  create: (data: TemplatePayload) =>
    http.post<ApiResponse<ResearchTemplate>, ApiResponse<ResearchTemplate>>("/research/templates", data),

  update: (id: string, data: Partial<TemplatePayload>) =>
    http.put<ApiResponse<ResearchTemplate>, ApiResponse<ResearchTemplate>>(`/research/templates/${id}`, data),

  remove: (id: string) =>
    http.delete<ApiResponse<null>, ApiResponse<null>>(`/research/templates/${id}`),
};

// ─── 上传（编辑器图片/附件）───────────────────────────────────────────────────

export const ResearchUploadAPI = {
  upload: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return http.post<ApiResponse<UploadResult>, ApiResponse<UploadResult>>("/research/upload", form, {
      headers: { "Content-Type": "multipart/form-data" },
    });
  },
};
