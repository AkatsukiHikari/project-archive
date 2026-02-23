import axios, {
  type AxiosError,
  type AxiosInstance,
  type AxiosResponse,
  type InternalAxiosRequestConfig,
} from "axios";
import qs from "qs";
import { config } from "./config";
import { useUserStore } from "@/stores/user";

const { result_code, base_url, request_timeout } = config;

/**
 * 标准后端响应格式
 */
interface ApiResponse<T = unknown> {
  code: number;
  data: T;
  message: string;
}

/**
 * 正在刷新令牌的标记
 */
let isRefreshToken = false;
/**
 * 因刷新令牌而暂停的请求队列
 */
const requestList: Array<() => void> = [];

/**
 * 创建 Axios 实例
 */
const service: AxiosInstance = axios.create({
  baseURL: base_url,
  timeout: request_timeout,
  // 参数序列化：处理 GET 请求数组
  paramsSerializer: (params) => {
    return qs.stringify(params, { allowDots: true });
  },
});

/**
 * 请求拦截器
 */
service.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const userStore = useUserStore();

    // 注入认证令牌
    if (userStore.token) {
      config.headers.Authorization = `Bearer ${userStore.token}`;
    }

    const method = config.method?.toUpperCase();
    // GET 请求处理：禁止缓存
    if (method === "GET") {
      config.headers["Cache-Control"] = "no-cache";
      config.headers["Pragma"] = "no-cache";
    }
    // POST 表单处理
    else if (method === "POST") {
      const contentType =
        config.headers["Content-Type"] || config.headers["content-type"];
      if (contentType === "application/x-www-form-urlencoded") {
        if (config.data && typeof config.data !== "string") {
          config.data = qs.stringify(config.data);
        }
      }
    }
    return config;
  },
  (error: AxiosError) => {
    return Promise.reject(error);
  },
);

/**
 * 响应拦截器
 *
 * 后端标准响应格式：{ code: number, data: T, message: string }
 * - code === 0  → 成功，返回整个响应体
 * - code === 1000/1001 → Token 过期/无效，跳登录
 * - code !== 0  → 业务错误，toast 提示并 reject
 */
service.interceptors.response.use(
  async (response: AxiosResponse<ApiResponse>) => {
    const { data: body } = response;

    if (!body) {
      return Promise.reject(new Error("接口响应无数据"));
    }

    // 二进制数据特殊处理（如 Excel 导出）
    if (
      response.request.responseType === "blob" ||
      response.request.responseType === "arraybuffer"
    ) {
      if ((body as unknown as Blob).type === "application/json") {
        // 后端实际返回了错误 JSON
        return new Response(body as unknown as Blob)
          .json()
          .then((parsed: ApiResponse) => {
            // if (import.meta.client) toast.error(parsed.message || "导出失败");
            return Promise.reject(new Error(parsed.message));
          });
      }
      // 真正的数据流，直接返回原始 response
      return response;
    }

    const { code, message: msg } = body;

    // 1. Token 过期或无效 → 跳 SSO 登录
    if (code === 1000 || code === 1001 || code === 1003) {
      if (!isRefreshToken) {
        isRefreshToken = true;
        if (import.meta.client) {
          // toast.error("会话已过期，请重新登录");
          const userStore = useUserStore();
          userStore.resetToken();
          // 触发 OAuth2 SSO 重新登录
          const { useAuth } = await import("@/hooks/useAuth");
          const { buildAuthorizeUrl } = useAuth();
          const url = await buildAuthorizeUrl(window.location.pathname);
          window.location.href = url;
        }
        return Promise.reject(new Error(msg));
      } else {
        return new Promise((resolve) => {
          requestList.push(() => {
            resolve(service(response.config));
          });
        });
      }
    }

    // 2. 业务错误 (code !== 0)
    if (code !== result_code) {
      if (import.meta.client) {
        // toast.error(msg || "请求失败");
      }
      return Promise.reject(new Error(msg));
    }

    // 3. 成功 (code === 0) — 返回完整 body，调用方通过 .data 取业务数据
    return body as unknown as AxiosResponse;
  },
  (error: AxiosError<ApiResponse>) => {
    let message = error.message;
    if (message === "Network Error") {
      message = "后端接口连接异常";
    } else if (message.includes("timeout")) {
      message = "系统接口请求超时";
    } else if (error.response?.data) {
      // 后端返回了标准错误体
      message =
        error.response.data.message || `系统接口 ${error.response.status} 异常`;
    }

    if (import.meta.client) {
      // toast.error(message);
    }
    return Promise.reject(error);
  },
);

export { service };
