/**
 * 系统数据字典 API 层
 */
import { service as http } from "@/utils/axios/service";

interface ApiResponse<T> {
  code: number;
  message: string;
  data: T;
}

// ─── 字典项 ──────────────────────────────────────────────────────────────────

export interface DictItem {
  id: string;
  dict_type: string;
  item_value: string;
  item_label: string;
  is_default: boolean;
  sort_order: number;
  description?: string;
}

export interface DictItemCreate {
  item_value: string;
  item_label: string;
  is_default?: boolean;
  sort_order?: number;
  description?: string;
}

export interface DictItemUpdate {
  item_value?: string;
  item_label?: string;
  is_default?: boolean;
  sort_order?: number;
  description?: string;
}

// ─── 字典类型 ────────────────────────────────────────────────────────────────

export interface SysDictSimple {
  id: string;
  dict_type: string;
  dict_name: string;
  description?: string;
  is_builtin: boolean;
  sort_order: number;
  item_count: number;
}

export interface DictCreate {
  dict_type: string;
  dict_name: string;
  description?: string;
  sort_order?: number;
}

export interface DictUpdate {
  dict_name?: string;
  description?: string;
  sort_order?: number;
}

// ─── API ─────────────────────────────────────────────────────────────────────

export const DictAPI = {
  // 字典类型
  list: () =>
    http.get<ApiResponse<SysDictSimple[]>, ApiResponse<SysDictSimple[]>>("/sys/dicts"),
  create: (data: DictCreate) =>
    http.post<ApiResponse<SysDictSimple>, ApiResponse<SysDictSimple>>("/sys/dicts", data),
  update: (dict_type: string, data: DictUpdate) =>
    http.put<ApiResponse<SysDictSimple>, ApiResponse<SysDictSimple>>(`/sys/dicts/${dict_type}`, data),
  remove: (dict_type: string) =>
    http.delete<ApiResponse<null>, ApiResponse<null>>(`/sys/dicts/${dict_type}`),

  // 字典项
  listItems: (dict_type: string) =>
    http.get<ApiResponse<DictItem[]>, ApiResponse<DictItem[]>>(`/sys/dicts/${dict_type}/items`),
  createItem: (dict_type: string, data: DictItemCreate) =>
    http.post<ApiResponse<DictItem>, ApiResponse<DictItem>>(`/sys/dicts/${dict_type}/items`, data),
  updateItem: (item_id: string, data: DictItemUpdate) =>
    http.put<ApiResponse<DictItem>, ApiResponse<DictItem>>(`/sys/dicts/items/${item_id}`, data),
  removeItem: (item_id: string) =>
    http.delete<ApiResponse<null>, ApiResponse<null>>(`/sys/dicts/items/${item_id}`),
};

/**
 * 便捷方法：将字典项转换为 Naive UI select options 格式
 */
export function dictToOptions(items: DictItem[]) {
  return items.map((i) => ({ label: i.item_label, value: i.item_value }));
}
