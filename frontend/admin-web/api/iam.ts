/**
 * IAM 模块 API 层
 * 所有 HTTP 调用集中于此，禁止在组件/页面内直接调用 axios
 */
import { service as http } from "@/utils/axios/service";

// ─── 通用后端响应包装 ───────────────────────────────────────────────
interface ApiResponse<T> {
  code: number;
  message: string;
  data: T;
}

// ─── 领域模型 (与后端 Pydantic schema 保持一致) ──────────────────────

export interface Tenant {
  id: string;
  name: string;
  code: string;
  description?: string;
  contact_person?: string;
  contact_email?: string;
  contact_phone?: string;
  status: "active" | "suspended" | "archived";
  is_default: boolean;
  create_time: string;
}

export interface Organization {
  id: string;
  tenant_id: string;
  parent_id?: string;
  name: string;
  code: string;
  sort_order: number;
  create_time: string;
}

export interface OrganizationTree extends Organization {
  children?: OrganizationTree[];
}

export interface Role {
  id: string;
  tenant_id: string;
  name: string;
  code: string;
  description?: string;
  create_time: string;
  menus?: Menu[];
}

export interface Menu {
  id: string;
  parent_id?: string;
  code: string;
  name: string;
  type: "DIR" | "MENU" | "BUTTON";
  path?: string;
  icon?: string;
  sort_order: number;
  is_visible: boolean;
  is_system: boolean;
  create_time: string;
}

export interface MenuTree extends Menu {
  children?: MenuTree[];
}

export interface User {
  id: string;
  tenant_id?: string;
  org_id?: string;
  username: string;
  email: string;
  full_name?: string;
  is_active: boolean;
  avatar?: string;
  phone?: string;
  job_title?: string;
  location?: string;
  bio?: string;
  last_login_time?: string;
  roles?: Role[];
  create_time: string;
}

export interface AuditLogItem {
  id: string;
  action: string;
  module: string;
  ip_address?: string;
  status: string;
  create_time: string;
  error_message?: string;
}

// ─── 请求体类型 ──────────────────────────────────────────────────────

export interface UserProfileUpdatePayload {
  full_name?: string;
  phone?: string;
  job_title?: string;
  location?: string;
  bio?: string;
}

export interface UserPasswordUpdatePayload {
  old_password: string;
  new_password: string;
}

export interface UserCreatePayload {
  username: string;
  email: string;
  password: string;
  full_name?: string;
  tenant_id?: string;
  org_id?: string;
  role_ids?: string[];
}

export interface UserUpdatePayload {
  email?: string;
  full_name?: string;
  is_active?: boolean;
  tenant_id?: string;
  org_id?: string;
  role_ids?: string[];
}

// ─── API 对象 ────────────────────────────────────────────────────────

export const TenantAPI = {
  list: () =>
    http.get<ApiResponse<Tenant[]>, ApiResponse<Tenant[]>>("/tenants"),
  get: (id: string) =>
    http.get<ApiResponse<Tenant>, ApiResponse<Tenant>>(`/tenants/${id}`),
  create: (data: Partial<Tenant>) =>
    http.post<ApiResponse<Tenant>, ApiResponse<Tenant>>("/tenants", data),
  update: (id: string, data: Partial<Tenant>) =>
    http.put<ApiResponse<Tenant>, ApiResponse<Tenant>>(`/tenants/${id}`, data),
  delete: (id: string) => http.delete(`/tenants/${id}`),
};

export const OrgAPI = {
  tree: (tenantId: string) =>
    http.get<ApiResponse<OrganizationTree[]>, ApiResponse<OrganizationTree[]>>(
      "/organizations/tree",
      { params: { tenant_id: tenantId } },
    ),
  get: (id: string) =>
    http.get<ApiResponse<Organization>, ApiResponse<Organization>>(
      `/organizations/${id}`,
    ),
  create: (data: Partial<Organization>) =>
    http.post<ApiResponse<Organization>, ApiResponse<Organization>>(
      "/organizations",
      data,
    ),
  update: (id: string, data: Partial<Organization>) =>
    http.put<ApiResponse<Organization>, ApiResponse<Organization>>(
      `/organizations/${id}`,
      data,
    ),
  delete: (id: string) => http.delete(`/organizations/${id}`),
};

export const RoleAPI = {
  list: (tenantId?: string) =>
    http.get<ApiResponse<Role[]>, ApiResponse<Role[]>>("/roles", {
      params: { tenant_id: tenantId },
    }),
  get: (id: string) =>
    http.get<ApiResponse<Role>, ApiResponse<Role>>(`/roles/${id}`),
  create: (data: Partial<Role> & { menu_ids?: string[] }) =>
    http.post<ApiResponse<Role>, ApiResponse<Role>>("/roles", data),
  update: (id: string, data: Partial<Role> & { menu_ids?: string[] }) =>
    http.put<ApiResponse<Role>, ApiResponse<Role>>(`/roles/${id}`, data),
  delete: (id: string) => http.delete(`/roles/${id}`),
};

export const MenuAPI = {
  tree: () =>
    http.get<ApiResponse<MenuTree[]>, ApiResponse<MenuTree[]>>("/menus/tree"),
  get: (id: string) =>
    http.get<ApiResponse<Menu>, ApiResponse<Menu>>(`/menus/${id}`),
  create: (data: Partial<Menu>) =>
    http.post<ApiResponse<Menu>, ApiResponse<Menu>>("/menus", data),
  update: (id: string, data: Partial<Menu>) =>
    http.put<ApiResponse<Menu>, ApiResponse<Menu>>(`/menus/${id}`, data),
  delete: (id: string) => http.delete(`/menus/${id}`),
};

export const UserAPI = {
  // ── 后台管理接口 ──
  list: (tenantId?: string, orgId?: string) =>
    http.get<ApiResponse<User[]>, ApiResponse<User[]>>("/users", {
      params: { tenant_id: tenantId, org_id: orgId },
    }),
  get: (id: string) =>
    http.get<ApiResponse<User>, ApiResponse<User>>(`/users/${id}`),
  create: (data: UserCreatePayload) =>
    http.post<ApiResponse<User>, ApiResponse<User>>("/users", data),
  update: (id: string, data: UserUpdatePayload) =>
    http.put<ApiResponse<User>, ApiResponse<User>>(`/users/${id}`, data),
  delete: (id: string) => http.delete(`/users/${id}`),

  // ── 个人中心接口 ──
  getProfile: () => http.get<ApiResponse<User>, ApiResponse<User>>("/users/me"),
  updateProfile: (data: UserProfileUpdatePayload) =>
    http.put<ApiResponse<User>, ApiResponse<User>>("/users/me/profile", data),
  updatePassword: (data: UserPasswordUpdatePayload) =>
    http.put<
      ApiResponse<{ message: string }>,
      ApiResponse<{ message: string }>
    >("/users/me/password", data),
  uploadAvatar: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return http.post<
      ApiResponse<{ avatar_url: string }>,
      ApiResponse<{ avatar_url: string }>
    >("/users/me/avatar", form, {
      headers: { "Content-Type": "multipart/form-data" },
    });
  },
  getMyAuditLogs: (params?: { skip?: number; limit?: number }) =>
    http.get<ApiResponse<AuditLogItem[]>, ApiResponse<AuditLogItem[]>>(
      "/audits/me",
      { params },
    ),
};
