import { service as http } from "@/utils/axios/service";

// Types
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
  is_system: boolean;
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
  full_name: string;
  is_active: boolean;
  roles?: Role[];
  create_time: string;
}

// ------ Tenants ------
export const TenantAPI = {
  list: () => http.get<any, { data: Tenant[] }>("/tenants"),
  get: (id: string) => http.get<any, { data: Tenant }>(`/tenants/${id}`),
  create: (data: Partial<Tenant>) =>
    http.post<any, { data: Tenant }>("/tenants", data),
  update: (id: string, data: Partial<Tenant>) =>
    http.put<any, { data: Tenant }>(`/tenants/${id}`, data),
  delete: (id: string) => http.delete(`/tenants/${id}`),
};

// ------ Organizations ------
export const OrgAPI = {
  tree: (tenantId: string) =>
    http.get<any, { data: OrganizationTree[] }>("/organizations/tree", {
      params: { tenant_id: tenantId },
    }),
  get: (id: string) =>
    http.get<any, { data: Organization }>(`/organizations/${id}`),
  create: (data: Partial<Organization>) =>
    http.post<any, { data: Organization }>("/organizations", data),
  update: (id: string, data: Partial<Organization>) =>
    http.put<any, { data: Organization }>(`/organizations/${id}`, data),
  delete: (id: string) => http.delete(`/organizations/${id}`),
};

// ------ Roles ------
export const RoleAPI = {
  list: (tenantId?: string) =>
    http.get<any, { data: Role[] }>("/roles", {
      params: { tenant_id: tenantId },
    }),
  get: (id: string) => http.get<any, { data: Role }>(`/roles/${id}`),
  create: (data: Partial<Role> & { menu_ids?: string[] }) =>
    http.post<any, { data: Role }>("/roles", data),
  update: (id: string, data: Partial<Role> & { menu_ids?: string[] }) =>
    http.put<any, { data: Role }>(`/roles/${id}`, data),
  delete: (id: string) => http.delete(`/roles/${id}`),
};

// ------ Menus ------
export const MenuAPI = {
  tree: () => http.get<any, { data: MenuTree[] }>("/menus/tree"),
  get: (id: string) => http.get<any, { data: Menu }>(`/menus/${id}`),
  create: (data: Partial<Menu>) =>
    http.post<any, { data: Menu }>("/menus", data),
  update: (id: string, data: Partial<Menu>) =>
    http.put<any, { data: Menu }>(`/menus/${id}`, data),
  delete: (id: string) => http.delete(`/menus/${id}`),
};

// ------ Users ------
export const UserAPI = {
  list: (tenantId?: string, orgId?: string) =>
    http.get<any, { data: User[] }>("/users", {
      params: { tenant_id: tenantId, org_id: orgId },
    }),
  get: (id: string) => http.get<any, { data: User }>(`/users/${id}`),
  create: (data: Partial<User> & { password?: string; role_ids?: string[] }) =>
    http.post<any, { data: User }>("/users", data),
  update: (
    id: string,
    data: Partial<User> & { password?: string; role_ids?: string[] },
  ) => http.put<any, { data: User }>(`/users/${id}`, data),
  delete: (id: string) => http.delete(`/users/${id}`),
};
