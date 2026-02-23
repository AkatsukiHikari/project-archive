// 后端接口响应标准结构
// code=0 为成功，非 0 为业务错误码
export interface ApiResponse<T = unknown> {
  code: number;
  data: T;
  message: string;
}

// 登录接口返回的 data 字段结构
export interface LoginResult {
  access_token: string;
  token_type: string;
}

// 用户信息结构
export interface UserInfo {
  id: string;
  username: string;
  email: string;
  full_name?: string;
  roles: string[];
  avatar?: string;
}

// 分页查询参数
export interface PageQuery {
  page: number;
  size: number;
  [key: string]: unknown;
}

// 分页响应结构
export interface PageResult<T> {
  list: T[];
  total: number;
  page: number;
  size: number;
}
