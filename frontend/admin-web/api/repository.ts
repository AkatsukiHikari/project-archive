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

export const CatalogAPI = {
  list: (fonds_id: string) =>
    http.get<ApiResponse<Catalog[]>, ApiResponse<Catalog[]>>("/archive/catalogs", { params: { fonds_id } }),
  create: (data: CatalogCreate) => http.post<ApiResponse<Catalog>, ApiResponse<Catalog>>("/archive/catalogs", data),
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
  status: string;
  ext_fields?: Record<string, unknown>;
  embedding_status: string;
  tenant_id?: string;
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

export const ArchiveAPI = {
  list: (params: ArchiveListParams) =>
    http.get<ApiResponse<ArchiveListResult>, ApiResponse<ArchiveListResult>>("/archive/records", { params }),
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
