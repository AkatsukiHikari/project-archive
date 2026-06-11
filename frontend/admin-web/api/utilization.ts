/**
 * 档案利用 API 层：利用申请（利用登记）+ 调阅篮
 */
import { service as http } from "@/utils/axios/service";

interface ApiResponse<T> {
  code: number;
  message: string;
  data: T;
}

export type UseType = "read" | "borrow" | "copy" | "certificate";
export type AppStatus = "processing" | "completed" | "cancelled";

export interface UtilApplication {
  id: string;
  reg_no: string;
  applicant_name: string;
  id_card_no?: string | null;
  gender?: string | null;
  phone?: string | null;
  organization?: string | null;
  avatar_key?: string | null;
  purpose?: string | null;
  use_type: string;
  status: AppStatus;
  handler_id?: string | null;
  handler_name?: string | null;
  completed_at?: string | null;
  create_time: string;
  item_count: number;
  // 业务字段
  borrowed_at?: string | null;
  due_date?: string | null;
  returned_at?: string | null;
  copy_method?: string | null;
  copies?: number | null;
  fee?: number | null;
  delivered_at?: string | null;
  cert_no?: string | null;
  cert_content?: string | null;
  issued_at?: string | null;
  biz_status?: string | null;
}

export interface UtilItem {
  id: string;
  archive_id: string;
  DH?: string | null;
  TM: string;
  RZZ?: string | null;
  ND?: number | null;
  QZH?: string | null;
  create_time: string;
}

export interface UtilApplicationDetail extends UtilApplication {
  items: UtilItem[];
}

export interface ApplicationCreate {
  applicant_name: string;
  id_card_no?: string | null;
  gender?: string | null;
  phone?: string | null;
  organization?: string | null;
  purpose?: string | null;
  use_type?: string;
  avatar_key?: string | null;
}

export interface ItemIn {
  archive_id: string;
  DH?: string | null;
  TM: string;
  RZZ?: string | null;
  ND?: number | null;
  QZH?: string | null;
}

export interface UtilLedgerRow {
  reg_no: string;
  applicant_name: string;
  organization?: string | null;
  use_type: string;
  purpose?: string | null;
  archive_id: string;
  DH?: string | null;
  TM: string;
  ND?: number | null;
  handler_name?: string | null;
  status: AppStatus;
  used_at?: string | null;
}

export interface LedgerQuery {
  status?: string;
  use_type?: string;
  keyword?: string;
  date_from?: string;
  date_to?: string;
}

export interface LedgerStats {
  summary: { items: number; applications: number; archives: number };
  by_period: { period: string; count: number }[];
  by_purpose: { name: string; count: number }[];
  by_use_type: { name: string; count: number }[];
  by_category: { category_id: string; count: number }[];
}

const BASE = "/utilization/applications";

export const UtilizationAPI = {
  ledger: (params?: LedgerQuery) =>
    http.get<ApiResponse<UtilLedgerRow[]>, ApiResponse<UtilLedgerRow[]>>("/utilization/ledger", { params: params ?? {} }),
  ledgerStats: (params?: { granularity?: string; date_from?: string; date_to?: string }) =>
    http.get<ApiResponse<LedgerStats>, ApiResponse<LedgerStats>>("/utilization/ledger/stats", { params: params ?? {} }),
  list: (params?: { status?: string; use_type?: string; keyword?: string }) =>
    http.get<ApiResponse<UtilApplication[]>, ApiResponse<UtilApplication[]>>(BASE, { params: params ?? {} }),
  create: (body: ApplicationCreate) =>
    http.post<ApiResponse<UtilApplication>, ApiResponse<UtilApplication>>(BASE, body),
  lend: (id: string, due_date: string) =>
    http.post<ApiResponse<UtilApplication>, ApiResponse<UtilApplication>>(`${BASE}/${id}/lend`, { due_date }),
  renew: (id: string, due_date: string) =>
    http.post<ApiResponse<UtilApplication>, ApiResponse<UtilApplication>>(`${BASE}/${id}/renew`, { due_date }),
  returnBorrow: (id: string) =>
    http.post<ApiResponse<UtilApplication>, ApiResponse<UtilApplication>>(`${BASE}/${id}/return`, {}),
  processCopy: (id: string, body: { copy_method: string; copies: number; fee?: number | null }) =>
    http.post<ApiResponse<UtilApplication>, ApiResponse<UtilApplication>>(`${BASE}/${id}/copy`, body),
  issueCert: (id: string, cert_content: string) =>
    http.post<ApiResponse<UtilApplication>, ApiResponse<UtilApplication>>(`${BASE}/${id}/issue-cert`, { cert_content }),
  get: (id: string) =>
    http.get<ApiResponse<UtilApplicationDetail>, ApiResponse<UtilApplicationDetail>>(`${BASE}/${id}`),
  update: (id: string, body: Partial<ApplicationCreate>) =>
    http.put<ApiResponse<UtilApplication>, ApiResponse<UtilApplication>>(`${BASE}/${id}`, body),
  complete: (id: string) =>
    http.post<ApiResponse<UtilApplication>, ApiResponse<UtilApplication>>(`${BASE}/${id}/complete`, {}),
  cancel: (id: string) =>
    http.post<ApiResponse<UtilApplication>, ApiResponse<UtilApplication>>(`${BASE}/${id}/cancel`, {}),
  addItems: (id: string, items: ItemIn[]) =>
    http.post<ApiResponse<{ added: number }>, ApiResponse<{ added: number }>>(`${BASE}/${id}/items`, { items }),
  removeItem: (id: string, itemId: string) =>
    http.delete<ApiResponse<null>, ApiResponse<null>>(`${BASE}/${id}/items/${itemId}`),
};
