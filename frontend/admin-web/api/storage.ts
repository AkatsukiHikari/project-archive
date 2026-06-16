/**
 * 档案保管 API 层：库房 / 出入库 / 保管台账
 */
import { service as http } from "@/utils/axios/service";

interface ApiResponse<T> {
  code: number;
  message: string;
  data: T;
}

// ─── 类型 ─────────────────────────────────────────────────────────────────────

export type VaultStatus = "active" | "maintenance" | "disabled";
export type InoutDirection = "out" | "in";
export type InoutBizType = "borrow" | "repair" | "digitize" | "relocate" | "inventory" | "other";
export type InoutStatus = "out" | "returned" | "done";

export interface Shelf {
  id: string;
  code: string;
  row_index: number;
  col_index: number;
  capacity: number;
  used: number;
  label?: string | null;
}

export interface Vault {
  id: string;
  code: string;
  name: string;
  location?: string | null;
  area_sqm?: number | null;
  rows: number;
  columns: number;
  layers: number;
  capacity: number;
  used: number;
  temperature?: number | null;
  humidity?: number | null;
  status: VaultStatus;
  manager_id?: string | null;
  notes?: string | null;
  fill_rate: number;
  shelves?: Shelf[];
}

export interface VaultPayload {
  code?: string;
  name?: string;
  location?: string;
  area_sqm?: number;
  rows?: number;
  columns?: number;
  layers?: number;
  capacity?: number;
  temperature?: number;
  humidity?: number;
  status?: VaultStatus;
  notes?: string;
}

export interface InoutRecord {
  id: string;
  record_no: string;
  direction: InoutDirection;
  biz_type: InoutBizType;
  archive_id?: string | null;
  DH?: string | null;
  TM?: string | null;
  qty: number;
  vault_id?: string | null;
  counterparty?: string | null;
  related_app_id?: string | null;
  status: InoutStatus;
  out_time?: string | null;
  expected_return?: string | null;
  in_time?: string | null;
  operator_id?: string | null;
  notes?: string | null;
  create_time: string;
}

export interface InoutPayload {
  direction: InoutDirection;
  biz_type: InoutBizType;
  archive_id?: string;
  DH?: string;
  TM?: string;
  qty?: number;
  vault_id?: string;
  counterparty?: string;
  expected_return?: string;
  notes?: string;
}

export interface StorageLedger {
  summary: {
    vault_count: number;
    total_capacity: number;
    total_used: number;
    fill_rate: number;
    out_active: number;
    inout_total: number;
  };
  vaults: Vault[];
}

// ─── API ─────────────────────────────────────────────────────────────────────

export const StorageAPI = {
  listVaults: () => http.get<ApiResponse<Vault[]>, ApiResponse<Vault[]>>("/storage/vaults"),
  getVault: (id: string) => http.get<ApiResponse<Vault>, ApiResponse<Vault>>(`/storage/vaults/${id}`),
  createVault: (data: VaultPayload) => http.post<ApiResponse<Vault>, ApiResponse<Vault>>("/storage/vaults", data),
  updateVault: (id: string, data: VaultPayload) => http.put<ApiResponse<Vault>, ApiResponse<Vault>>(`/storage/vaults/${id}`, data),
  deleteVault: (id: string) => http.delete<ApiResponse<null>, ApiResponse<null>>(`/storage/vaults/${id}`),

  listInout: (params?: {
    direction?: InoutDirection;
    biz_type?: InoutBizType;
    status?: InoutStatus;
    keyword?: string;
    skip?: number;
    limit?: number;
  }) =>
    http.get<ApiResponse<{ total: number; items: InoutRecord[] }>, ApiResponse<{ total: number; items: InoutRecord[] }>>(
      "/storage/inout", { params },
    ),
  createInout: (data: InoutPayload) => http.post<ApiResponse<InoutRecord>, ApiResponse<InoutRecord>>("/storage/inout", data),
  returnInout: (id: string) => http.post<ApiResponse<InoutRecord>, ApiResponse<InoutRecord>>(`/storage/inout/${id}/return`),

  ledger: () => http.get<ApiResponse<StorageLedger>, ApiResponse<StorageLedger>>("/storage/ledger"),

  // 架位管理
  getShelf: (id: string) => http.get<ApiResponse<ShelfDetail>, ApiResponse<ShelfDetail>>(`/storage/shelves/${id}`),
  updateShelf: (id: string, data: { capacity?: number; label?: string }) =>
    http.put<ApiResponse<null>, ApiResponse<null>>(`/storage/shelves/${id}`, data),
  assignToShelf: (id: string, archiveIds: string[]) =>
    http.post<ApiResponse<{ assigned: number }>, ApiResponse<{ assigned: number }>>(`/storage/shelves/${id}/assign`, { archive_ids: archiveIds }),
  unassignFromShelf: (archiveIds: string[]) =>
    http.post<ApiResponse<{ unassigned: number }>, ApiResponse<{ unassigned: number }>>("/storage/shelves/unassign", { archive_ids: archiveIds }),
  unshelved: (keyword?: string) =>
    http.get<ApiResponse<ShelfArchive[]>, ApiResponse<ShelfArchive[]>>("/storage/unshelved", { params: keyword ? { keyword } : {} }),
};

export interface ShelfArchive {
  id: string;
  DH?: string | null;
  TM: string;
  ND?: number | null;
  QZH?: string | null;
}

export interface ShelfDetail {
  id: string;
  code: string;
  capacity: number;
  used: number;
  label?: string | null;
  archives: ShelfArchive[];
}
