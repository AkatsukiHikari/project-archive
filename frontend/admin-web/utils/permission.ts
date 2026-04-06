import { useUserStore } from "@/stores/user";

/**
 * 全局权限判断工具
 * @param requiredPermissions 需要的权限码列表 (单个字符串或数组)
 * @returns boolean 是否拥有权限
 */
export function hasPermission(requiredPermissions: string | string[]): boolean {
  const userStore = useUserStore();
  const userPerms = userStore.permissions || [];

  if (!requiredPermissions || requiredPermissions.length === 0) {
    return true;
  }

  // 超级管理员/系统管理员一票放行
  if (
    userStore.roles.includes("admin") ||
    userStore.roles.includes("superadmin")
  ) {
    return true;
  }

  const reqs = Array.isArray(requiredPermissions)
    ? requiredPermissions
    : [requiredPermissions];

  // 必须满足全部指定的权限点
  return reqs.every((p) => userPerms.includes(p));
}
