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

// 角色信息（与后端 Role schema 一致）
export interface RoleInfo {
  id: string;
  name: string;
  code: string;
  description?: string;
  menus?: any[];
}

// 用户信息结构（与后端 User schema 一致）
export interface UserInfo {
  id: string;
  username: string;
  email: string;
  full_name?: string;
  avatar?: string;
  phone?: string;
  job_title?: string;
  location?: string;
  bio?: string;
  is_active: boolean;
  is_superadmin?: boolean;
  tenant_id?: string;
  org_id?: string;
  last_login_time?: string;
  create_time?: string;
  /** 角色对象列表 */
  roles: RoleInfo[];
  /** 角色码列表（从 roles 派生，供权限判断使用） */
  roleCodes: string[];
  /** 真实的细粒度权限标识列表 */
  permissions?: string[];
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
