/**
 * 档案库模块 API 层
 * 覆盖：全宗 / 门类 / 目录 / 档案
 */
import { service as http } from "@/utils/axios/service";

interface ApiResponse<T> {
  code: number;
  message: string;
  data: T;
}

// ─── 全宗 ────────────────────────────────────────────────────────────────────

export interface Fonds {
  id: string;
  fonds_code: string;
  name: string;
  short_name?: string;
  description?: string;
  start_year?: number;
  end_year?: number;
  retention_period: string;
  status: string;
  custodian_id?: string;
  tenant_id?: string;
  create_time?: string;
}

export interface FondsCreate {
  fonds_code: string;
  name: string;
  short_name?: string;
  description?: string;
  start_year?: number;
  end_year?: number;
  retention_period?: string;
  status?: string;
}

export interface FondsUpdate {
  name?: string;
  short_name?: string;
  description?: string;
  start_year?: number;
  end_year?: number;
  retention_period?: string;
  status?: string;
}

export const FondsAPI = {
  list: () => http.get<ApiResponse<Fonds[]>, ApiResponse<Fonds[]>>("/archive/fonds"),
  create: (data: FondsCreate) => http.post<ApiResponse<Fonds>, ApiResponse<Fonds>>("/archive/fonds", data),
  update: (id: string, data: FondsUpdate) =>
    http.put<ApiResponse<Fonds>, ApiResponse<Fonds>>(`/archive/fonds/${id}`, data),
  remove: (id: string) => http.delete<ApiResponse<null>, ApiResponse<null>>(`/archive/fonds/${id}`),
};

// ─── 门类 ────────────────────────────────────────────────────────────────────

export interface FieldDefinition {
  name: string;
  label: string;
  type: "text" | "number" | "date" | "select" | "boolean" | "textarea";
  required?: boolean;
  placeholder?: string;
  options?: string[];
  dict_type?: string;
  default_value?: string | number | boolean | null;
  sort_order?: number;
  inherited?: boolean;
}

export interface FormLayoutCell {
  field: string;  // FieldDefinition.name
  span: 1 | 2;   // 1=半行 2=整行
}

export interface FormLayoutRow {
  id: string;
  cells: FormLayoutCell[];
}

export interface FormLayout {
  cols: 2;
  rows: FormLayoutRow[];
}

export interface ArchiveCategory {
  id: string;
  code: string;
  name: string;
  parent_id?: string;
  base_category_id?: string;
  is_builtin: boolean;
  requires_privacy_guard: boolean;
  field_schema?: FieldDefinition[];
  form_layout?: FormLayout | null;
  tenant_id?: string;
}

export interface CategoryCreate {
  code: string;
  name: string;
  parent_id?: string;
  requires_privacy_guard?: boolean;
  field_schema?: FieldDefinition[];
}

export interface CategoryUpdate {
  name?: string;
  requires_privacy_guard?: boolean;
  field_schema?: FieldDefinition[];
}

export const CategoryAPI = {
  list: (parent_id?: string) =>
    http.get<ApiResponse<ArchiveCategory[]>, ApiResponse<ArchiveCategory[]>>("/archive/categories", {
      params: parent_id ? { parent_id } : {},
    }),
  create: (data: CategoryCreate) =>
    http.post<ApiResponse<ArchiveCategory>, ApiResponse<ArchiveCategory>>("/archive/categories", data),
  clone: (id: string, new_code: string, new_name: string) =>
    http.post<ApiResponse<ArchiveCategory>, ApiResponse<ArchiveCategory>>(`/archive/categories/${id}/clone`, null, {
      params: { new_code, new_name },
    }),
  update: (id: string, data: CategoryUpdate) =>
    http.put<ApiResponse<ArchiveCategory>, ApiResponse<ArchiveCategory>>(`/archive/categories/${id}`, data),
  remove: (id: string) => http.delete<ApiResponse<null>, ApiResponse<null>>(`/archive/categories/${id}`),
  getSchema: (id: string) =>
    http.get<ApiResponse<FieldDefinition[]>, ApiResponse<FieldDefinition[]>>(`/archive/categories/${id}/schema`),
  updateSchema: (id: string, fields: FieldDefinition[]) =>
    http.put<ApiResponse<FieldDefinition[]>, ApiResponse<FieldDefinition[]>>(`/archive/categories/${id}/schema`, fields),
  getLayout: (id: string) =>
    http.get<ApiResponse<FormLayout | null>, ApiResponse<FormLayout | null>>(`/archive/categories/${id}/layout`),
  updateLayout: (id: string, layout: FormLayout) =>
    http.put<ApiResponse<FormLayout>, ApiResponse<FormLayout>>(`/archive/categories/${id}/layout`, layout),
};

// ─── 目录 ────────────────────────────────────────────────────────────────────

export type CatalogType = "案卷目录" | "卷内目录" | "一文一件";

export interface Catalog {
  id: string;
  fonds_id: string;
  category_id: string;
  catalog_no: string;
  name: string;
  year?: number;
  catalog_type: CatalogType;
  volume_archive_id?: string;
  tenant_id?: string;
}

export interface CatalogCreate {
  fonds_id: string;
  category_id: string;
  catalog_no: string;
  name: string;
  year?: number;
  catalog_type?: CatalogType;
  volume_archive_id?: string;
}

export interface CatalogUpdate {
  name?: string;
  year?: number | null;
  catalog_type?: CatalogType;
  volume_archive_id?: string | null;
}

export const CatalogAPI = {
  list: (fonds_id: string) =>
    http.get<ApiResponse<Catalog[]>, ApiResponse<Catalog[]>>("/archive/catalogs", { params: { fonds_id } }),
  create: (data: CatalogCreate) => http.post<ApiResponse<Catalog>, ApiResponse<Catalog>>("/archive/catalogs", data),
  update: (id: string, data: CatalogUpdate) =>
    http.put<ApiResponse<Catalog>, ApiResponse<Catalog>>(`/archive/catalogs/${id}`, data),
  remove: (id: string) => http.delete<ApiResponse<null>, ApiResponse<null>>(`/archive/catalogs/${id}`),
};


// ─── 档案 ────────────────────────────────────────────────────────────────────

export interface Archive {
  id: string;
  fonds_id: string;
  catalog_id: string;
  category_id: string;
  DH?: string;
  QZH: string;
  TM: string;
  RZZ?: string;
  ND?: number;
  WJRQ?: string;
  YS?: number;
  MJ: string;
  BGQX: string;
  KFZT?: string | null;
  status: string;
  ext_fields?: Record<string, unknown>;
  embedding_status: string;
  tenant_id?: string;
  attachment_count?: number;
}

// ─── 档号规则 ─────────────────────────────────────────────────────────────────

export type SegmentType = "field" | "literal" | "sequence" | "date_part";
export type SeqScope = "catalog" | "catalog_year" | "fonds";

export interface SegmentDef {
  type: SegmentType;
  field?: string;
  value?: string;
  padding?: number;
  scope?: SeqScope;
  date_field?: string;
  date_format?: string;
}

export interface RuleTemplate {
  separator: string;
  segments: SegmentDef[];
}

export interface NoRule {
  id: string;
  category_id: string;
  name: string;
  rule_template: RuleTemplate | null;
  seq_scope: SeqScope;
  is_active: boolean;
  tenant_id?: string;
  create_time?: string;
}

export interface NoRuleCreate {
  category_id: string;
  name: string;
  rule_template: RuleTemplate;
  seq_scope?: SeqScope;
  is_active?: boolean;
}

export interface NoRuleUpdate {
  name?: string;
  rule_template?: RuleTemplate;
  seq_scope?: SeqScope;
  is_active?: boolean;
}

export interface PreviewSample {
  QZH?: string;
  ND?: number;
  RZZ?: string;
  WJRQ?: string;
}

export interface PreviewResponse {
  DH: string;
  segments: string[];
}

export const NoRuleAPI = {
  list: () => http.get<ApiResponse<NoRule[]>, ApiResponse<NoRule[]>>("/archive/no-rules"),
  create: (data: NoRuleCreate) =>
    http.post<ApiResponse<NoRule>, ApiResponse<NoRule>>("/archive/no-rules", data),
  update: (id: string, data: NoRuleUpdate) =>
    http.put<ApiResponse<NoRule>, ApiResponse<NoRule>>(`/archive/no-rules/${id}`, data),
  remove: (id: string) =>
    http.delete<ApiResponse<null>, ApiResponse<null>>(`/archive/no-rules/${id}`),
  preview: (id: string, sample: PreviewSample) =>
    http.post<ApiResponse<PreviewResponse>, ApiResponse<PreviewResponse>>(
      `/archive/no-rules/${id}/preview`,
      sample,
    ),
};

// ─── 档案记录 ─────────────────────────────────────────────────────────────────

export interface ArchiveCreate {
  fonds_id: string;
  catalog_id: string;
  category_id: string;
  TM: string;
  QZH: string;
  ND?: number;
  RZZ?: string;
  DH?: string;
  MJ?: string;
  BGQX?: string;
  WJRQ?: string;
  YS?: number;
  ext_fields?: Record<string, unknown>;
}

export interface ArchiveUpdate {
  TM?: string;
  RZZ?: string;
  ND?: number;
  MJ?: string;
  BGQX?: string;
  WJRQ?: string;
  YS?: number;
  status?: string;
  ext_fields?: Record<string, unknown>;
  DH?: string;
}

export interface ArchiveListResult {
  total: number;
  page: number;
  page_size: number;
  items: Archive[];
}

export interface ArchiveListParams {
  fonds_id?: string;
  catalog_id?: string;
  category_id?: string;
  ND?: number;
  keyword?: string;
  MJ?: string;
  status?: string;
  TM?: string;
  RZZ?: string;
  DH?: string;
  BGQX?: string;
  ND_from?: number;
  ND_to?: number;
  WJRQ_from?: string;
  WJRQ_to?: string;
  page?: number;
  page_size?: number;
}

export interface ArchiveAttachment {
  id: string;
  archive_id: string;
  is_primary: boolean;
  original_name: string;
  storage_key: string;
  storage_bucket: string;
  file_size?: number | null;
  file_format?: string | null;
  page_count?: number | null;
  sort_order: number;
  url: string | null;
}

export interface NavCategory { category_id: string; code: string; name: string; count: number }
export interface NavFonds { qzh: string; fonds_id: string; count: number }
export interface NavYear { year: number; count: number }

export const ArchiveAPI = {
  list: (params: ArchiveListParams) =>
    http.get<ApiResponse<ArchiveListResult>, ApiResponse<ArchiveListResult>>("/archive/records", { params }),
  navCategories: () =>
    http.get<ApiResponse<NavCategory[]>, ApiResponse<NavCategory[]>>("/archive/records/nav", { params: { level: "category" } }),
  navFonds: (categoryId: string) =>
    http.get<ApiResponse<NavFonds[]>, ApiResponse<NavFonds[]>>("/archive/records/nav", { params: { level: "fonds", category_id: categoryId } }),
  navYears: (categoryId: string, fondsId: string) =>
    http.get<ApiResponse<NavYear[]>, ApiResponse<NavYear[]>>("/archive/records/nav", { params: { level: "year", category_id: categoryId, fonds_id: fondsId } }),
  get: (id: string) => http.get<ApiResponse<Archive>, ApiResponse<Archive>>(`/archive/records/${id}`),
  attachments: (id: string) =>
    http.get<ApiResponse<ArchiveAttachment[]>, ApiResponse<ArchiveAttachment[]>>(`/archive/records/${id}/attachments`),
  create: (data: ArchiveCreate) => http.post<ApiResponse<Archive>, ApiResponse<Archive>>("/archive/records", data),
  update: (id: string, data: ArchiveUpdate) =>
    http.put<ApiResponse<Archive>, ApiResponse<Archive>>(`/archive/records/${id}`, data),
  remove: (id: string) => http.delete<ApiResponse<null>, ApiResponse<null>>(`/archive/records/${id}`),
  overrideNo: (id: string, DH: string) =>
    http.patch<ApiResponse<Archive>, ApiResponse<Archive>>(`/archive/records/${id}/override-no`, { DH }),
};

// ─── 档案整理（批量修改 / 重编档号 / 挂接数字化成果 / 归档入库） ──────────────

export interface BatchUpdatePayload {
  ids: string[];
  MJ?: string;
  BGQX?: string;
  RZZ?: string;
  ND?: number;
  WJRQ?: string;
}

export interface RenumberPayload {
  rule_id: string;
  catalog_id?: string;
  ids?: string[];
  /** 按当前查询条件全量应用（与著录列表同一套条件，跨页生效） */
  query?: Partial<ArchiveListParams>;
  start_seq?: number;
}

export interface RenumberRow {
  id: string;
  TM: string;
  WJRQ?: string | null;
  DH_old?: string | null;
  DH_new: string;
  conflict: boolean;
}

export interface RenumberPreviewResult {
  total: number;
  conflicts: number;
  rows: RenumberRow[];
}

export type AttachRowStatus =
  | "matched" | "not_found" | "has_primary"   // 预检
  | "attached" | "skipped";                    // 执行

export interface AttachMatchRow {
  filename: string;
  DH: string;
  status: AttachRowStatus;
  source?: "staging" | "formal" | null;
  archive_id?: string | null;
  TM?: string | null;
  reason?: string | null;
}

export interface AttachPreviewResult {
  total: number;
  matched: number;
  not_found: number;
  has_primary: number;
  rows: AttachMatchRow[];
}

export interface AttachBatchResult {
  batch_no: string;
  attached: number;
  skipped: number;
  not_found: number;
  rows: AttachMatchRow[];
}

export interface AttachBatchRecord {
  id: string;
  batch_no: string;
  total: number;
  attached: number;
  skipped: number;
  not_found: number;
  overwrite: boolean;
  create_time: string | null;
  rows?: AttachMatchRow[];
}

export interface ArchiveToFormalRow {
  id: string;
  DH?: string | null;
  TM: string;
  status: "ok" | "failed";
  reason?: string | null;
}

export interface ArchiveToFormalResult {
  archived: number;
  failed: number;
  rows: ArchiveToFormalRow[];
}

export const OrganizeAPI = {
  batchUpdate: (data: BatchUpdatePayload) =>
    http.put<ApiResponse<{ updated: number }>, ApiResponse<{ updated: number }>>(
      "/archive/organize/records/batch", data,
    ),

  batchDelete: (ids: string[]) =>
    http.post<ApiResponse<{ deleted: number }>, ApiResponse<{ deleted: number }>>(
      "/archive/organize/records/batch-delete", { ids },
    ),

  /** 自动档号：有历史→末位+1；无历史→按门类档号规则生成第一条 */
  nextDh: (categoryId: string, ctx?: { qzh?: string; nd?: number; fonds_id?: string; catalog_id?: string }) =>
    http.get<ApiResponse<{ dh: string }>, ApiResponse<{ dh: string }>>(
      "/archive/organize/next-dh",
      { params: { category_id: categoryId, ...ctx } },
    ),

  renumberPreview: (data: RenumberPayload) =>
    http.post<ApiResponse<RenumberPreviewResult>, ApiResponse<RenumberPreviewResult>>(
      "/archive/organize/renumber/preview", data,
    ),
  renumberApply: (data: RenumberPayload) =>
    http.post<ApiResponse<{ renumbered: number }>, ApiResponse<{ renumbered: number }>>(
      "/archive/organize/renumber/apply", data,
    ),

  attachPreview: (filenames: string[]) =>
    http.post<ApiResponse<AttachPreviewResult>, ApiResponse<AttachPreviewResult>>(
      "/archive/organize/attach/preview", { filenames },
    ),
  attachBatch: (files: File[], overwrite: boolean) => {
    const form = new FormData();
    files.forEach((f) => form.append("files", f));
    form.append("overwrite", String(overwrite));
    return http.post<ApiResponse<AttachBatchResult>, ApiResponse<AttachBatchResult>>(
      "/archive/organize/attach/batch", form,
      { headers: { "Content-Type": "multipart/form-data" } },
    );
  },

  listAttachBatches: (params?: { skip?: number; limit?: number }) =>
    http.get<ApiResponse<{ total: number; items: AttachBatchRecord[] }>, ApiResponse<{ total: number; items: AttachBatchRecord[] }>>(
      "/archive/organize/attach/batches", { params },
    ),
  getAttachBatch: (id: string) =>
    http.get<ApiResponse<AttachBatchRecord>, ApiResponse<AttachBatchRecord>>(
      `/archive/organize/attach/batches/${id}`,
    ),

  uploadAttachment: (archiveId: string, file: File, isPrimary = true) => {
    const form = new FormData();
    form.append("archive_id", archiveId);
    form.append("is_primary", String(isPrimary));
    form.append("file", file);
    return http.post<ApiResponse<ArchiveAttachment>, ApiResponse<ArchiveAttachment>>(
      "/archive/organize/attachments/upload", form,
      { headers: { "Content-Type": "multipart/form-data" } },
    );
  },
  deleteAttachment: (attachmentId: string) =>
    http.delete<ApiResponse<null>, ApiResponse<null>>(
      `/archive/organize/attachments/${attachmentId}`,
    ),
  setPrimaryAttachment: (attachmentId: string) =>
    http.patch<ApiResponse<ArchiveAttachment>, ApiResponse<ArchiveAttachment>>(
      `/archive/organize/attachments/${attachmentId}/primary`,
    ),

  archiveToFormal: (ids: string[]) =>
    http.post<ApiResponse<ArchiveToFormalResult>, ApiResponse<ArchiveToFormalResult>>(
      "/archive/organize/archive-to-formal", { ids },
    ),
};
