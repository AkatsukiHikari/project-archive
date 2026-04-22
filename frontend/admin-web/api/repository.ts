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
  list: () => http.get<ApiResponse<Fonds[]>>("/archive/fonds"),
  create: (data: FondsCreate) => http.post<ApiResponse<Fonds>>("/archive/fonds", data),
  update: (id: string, data: FondsUpdate) =>
    http.put<ApiResponse<Fonds>>(`/archive/fonds/${id}`, data),
  remove: (id: string) => http.delete<ApiResponse<null>>(`/archive/fonds/${id}`),
};

// ─── 门类 ────────────────────────────────────────────────────────────────────

export interface FieldDefinition {
  name: string;
  label: string;
  type: "text" | "number" | "date" | "select" | "boolean" | "textarea";
  required?: boolean;
  placeholder?: string;
  options?: string[];
  inherited?: boolean;
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
    http.get<ApiResponse<ArchiveCategory[]>>("/archive/categories", {
      params: parent_id ? { parent_id } : {},
    }),
  create: (data: CategoryCreate) =>
    http.post<ApiResponse<ArchiveCategory>>("/archive/categories", data),
  clone: (id: string, new_code: string, new_name: string) =>
    http.post<ApiResponse<ArchiveCategory>>(`/archive/categories/${id}/clone`, null, {
      params: { new_code, new_name },
    }),
  update: (id: string, data: CategoryUpdate) =>
    http.put<ApiResponse<ArchiveCategory>>(`/archive/categories/${id}`, data),
  remove: (id: string) => http.delete<ApiResponse<null>>(`/archive/categories/${id}`),
  getSchema: (id: string) =>
    http.get<ApiResponse<FieldDefinition[]>>(`/archive/categories/${id}/schema`),
  updateSchema: (id: string, fields: FieldDefinition[]) =>
    http.put<ApiResponse<FieldDefinition[]>>(`/archive/categories/${id}/schema`, fields),
};

// ─── 目录 ────────────────────────────────────────────────────────────────────

export interface Catalog {
  id: string;
  fonds_id: string;
  category_id: string;
  catalog_no: string;
  name: string;
  year?: number;
  org_mode: "by_item" | "by_volume";
  tenant_id?: string;
}

export interface CatalogCreate {
  fonds_id: string;
  category_id: string;
  catalog_no: string;
  name: string;
  year?: number;
  org_mode?: "by_item" | "by_volume";
}

export const CatalogAPI = {
  list: (fonds_id: string) =>
    http.get<ApiResponse<Catalog[]>>("/archive/catalogs", { params: { fonds_id } }),
  create: (data: CatalogCreate) => http.post<ApiResponse<Catalog>>("/archive/catalogs", data),
  remove: (id: string) => http.delete<ApiResponse<null>>(`/archive/catalogs/${id}`),
};

// ─── 档案 ────────────────────────────────────────────────────────────────────

export interface Archive {
  id: string;
  fonds_id: string;
  catalog_id: string;
  parent_id?: string;
  category_id: string;
  level: "volume" | "item";
  archive_no?: string;
  fonds_code: string;
  catalog_no?: string;
  volume_no?: string;
  item_no?: string;
  year?: number;
  title: string;
  creator?: string;
  security_level: string;
  retention_period: string;
  doc_date?: string;
  pages?: number;
  status: string;
  ext_fields?: Record<string, unknown>;
  file_format?: string;
  file_size?: number;
  embedding_status: string;
  tenant_id?: string;
}

export interface ArchiveCreate {
  fonds_id: string;
  catalog_id: string;
  category_id: string;
  level?: "volume" | "item";
  title: string;
  fonds_code: string;
  year?: number;
  creator?: string;
  catalog_no?: string;
  volume_no?: string;
  item_no?: string;
  archive_no?: string;
  security_level?: string;
  retention_period?: string;
  doc_date?: string;
  pages?: number;
  ext_fields?: Record<string, unknown>;
}

export interface ArchiveUpdate {
  title?: string;
  creator?: string;
  year?: number;
  security_level?: string;
  retention_period?: string;
  doc_date?: string;
  pages?: number;
  status?: string;
  ext_fields?: Record<string, unknown>;
  archive_no?: string;
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
  year?: number;
  keyword?: string;
  security_level?: string;
  status?: string;
  page?: number;
  page_size?: number;
}

export const ArchiveAPI = {
  list: (params: ArchiveListParams) =>
    http.get<ApiResponse<ArchiveListResult>>("/archive/records", { params }),
  get: (id: string) => http.get<ApiResponse<Archive>>(`/archive/records/${id}`),
  create: (data: ArchiveCreate) => http.post<ApiResponse<Archive>>("/archive/records", data),
  update: (id: string, data: ArchiveUpdate) =>
    http.put<ApiResponse<Archive>>(`/archive/records/${id}`, data),
  remove: (id: string) => http.delete<ApiResponse<null>>(`/archive/records/${id}`),
  overrideNo: (id: string, archive_no: string) =>
    http.patch<ApiResponse<Archive>>(`/archive/records/${id}/override-no`, { archive_no }),
};
