import type { InternalAxiosRequestConfig } from "axios";

/**
 * 接口响应基础结构
 */
export interface ApiResponse<T = unknown> {
  code: number;
  data: T;
  message: string;
}

/**
 * 扩展 Axios 请求配置
 */
export interface RequestOption extends Partial<InternalAxiosRequestConfig> {
  /** 接口地址 */
  url: string;
  /** 请求方式 */
  method?: "GET" | "POST" | "PUT" | "DELETE" | "PATCH";
  /** 请求头类型 */
  headersType?: string;
  /** 是否显示错误提示 */
  showError?: boolean;
  /** 是否需要携带 Token */
  withToken?: boolean;
  /** 扩展参数 */
  params?: Record<string, unknown>;
  /** 请求体数据 */
  data?: unknown;
}

/**
 * 认证令牌结构
 */
export interface AuthToken {
  accessToken: string;
  refreshToken: string;
}
