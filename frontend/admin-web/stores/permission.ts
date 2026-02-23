import { defineStore } from 'pinia';
import type { RouteRecordRaw } from 'vue-router';

/**
 * 辅助函数：判断路由是否有权限访问
 * @param roles 当前用户角色列表
 * @param route 路由对象
 */
function hasPermission(roles: string[], route: RouteRecordRaw): boolean {
  if (route.meta && route.meta.roles) {
    // 强制断言 meta.roles 为 string[]，需在 definePageMeta 中保证类型
    return roles.some(role => (route.meta!.roles as string[]).includes(role));
  }
  return true;
}

/**
 * 权限控制 Store
 */
export const usePermissionStore = defineStore('permission', {
  state: () => ({
    /** 侧边栏展示的菜单路由 */
    menuRoutes: [] as RouteRecordRaw[], 
  }),
  
  actions: {
    /**
     * 根据角色生成可访问的菜单路由
     * @param roles 角色列表
     * @param allRoutes 所有路由（通常由 router.getRoutes() 获取）
     */
    generateRoutes(roles: string[], allRoutes: RouteRecordRaw[]) {
      // 过滤 Nuxt 生成的路由用于菜单显示
      // 通常我们会过滤掉动态参数路由（包含 :）和 explicit hidden 路由
      const accessibleRoutes = allRoutes.filter(route => {
        // 排除隐藏路由、动态参数路由（除非作为子路由的父级）、重定向路由
        if (route.meta?.hidden) return false;
        if (route.path.includes(':') && !route.children) return false;
        
        if (hasPermission(roles, route)) {
          // 递归检查子路由
          if (route.children && route.children.length > 0) {
            route.children = route.children.filter((child) => hasPermission(roles, child));
          }
          return true;
        }
        return false;
      });
      
      this.menuRoutes = accessibleRoutes;
    }
  }
});