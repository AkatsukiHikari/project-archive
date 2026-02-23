/**
 * 接口请求全局配置
 */
export const config = {
  /**
   * 接口基础路径
   */
  base_url: import.meta.env.VITE_API_BASE_URL || "/api/v1",
  /**
   * 默认请求头
   */
  default_headers: "application/json;charset=utf-8",
  /**
   * 接口成功状态码（后端标准：code=0 为成功）
   */
  result_code: 0,
  /**
   * 请求超时时间（毫秒）
   */
  request_timeout: 30000,
};
