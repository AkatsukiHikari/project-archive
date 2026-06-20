/**
 * 超级查询 API（NDL 风格：字段/全文 + 分面聚合，全部走 ES）
 * 端点不在 v1 全局登录依赖下，按登录态分级（已登录看全部，匿名仅开放档案）。
 * 走现有 axios service：有 token 自动带上 → 全量；无 token → 开放档案。
 */
import { service as http } from "@/utils/axios/service";

interface ApiResponse<T> {
  code: number;
  message: string;
  data: T;
}

export type SearchMode = "field" | "fulltext";

export interface FacetValue {
  value: string | number;
  count: number;
  label: string;
}

export interface SearchHit {
  id: string;
  DH?: string;
  QZH?: string;
  TM: string;
  RZZ?: string;
  ND?: number;
  WJRQ?: string;
  MJ?: string;
  BGQX?: string;
  category_id?: string;
  score?: number;
  has_source?: boolean;
  full_text?: string;
  highlight?: { TM?: string[]; RZZ?: string[]; full_text?: string[] };
}

export interface SuperSearchResult {
  total: number;
  hits: SearchHit[];
  facets: Record<string, FacetValue[]>;
  facet_fields: string[];
  authed: boolean;
  error?: string | null;
}

export interface SuperSearchParams {
  keyword?: string;
  mode?: SearchMode;
  QZH?: string[];
  ND?: number[];
  RZZ?: string[];
  MJ?: string[];
  BGQX?: string[];
  category_id?: string[];
  page?: number;
  page_size?: number;
}

const FACET_KEYS = ["QZH", "ND", "RZZ", "MJ", "BGQX", "category_id"] as const;

export const SuperSearchAPI = {
  search: (params: SuperSearchParams) => {
    // 手工拼 query：数组要序列化成重复 key（QZH=a&QZH=b），FastAPI list 才能解析；
    // 直接走 service 的全局 paramsSerializer 会变成 QZH[0]=a（解析不到）。
    const sp = new URLSearchParams();
    if (params.keyword) sp.set("keyword", params.keyword);
    sp.set("mode", params.mode ?? "field");
    for (const key of FACET_KEYS) {
      const values = (params[key] ?? []) as (string | number)[];
      values.forEach((v) => sp.append(key, String(v)));
    }
    sp.set("page", String(params.page ?? 1));
    sp.set("page_size", String(params.page_size ?? 20));
    return http.get<ApiResponse<SuperSearchResult>, ApiResponse<SuperSearchResult>>(
      `/super-search/archive?${sp.toString()}`,
    );
  },
};
