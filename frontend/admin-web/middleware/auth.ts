import { useUserStore } from "@/stores/user";
import { useAuth } from "@/hooks/useAuth";

/**
 * 全局路由守卫 —— SSO 认证中间件
 *
 * 逻辑：
 * 1. 白名单页面（callback 等）直接放行
 * 2. 无 token → navigateTo 到 OAuth2 授权端点（无闪烁）
 * 3. 有 token 但无用户信息 → 拉取用户信息
 */
export default defineNuxtRouteMiddleware(async (to) => {
  const userStore = useUserStore();
  const token = userStore.token;

  // 不需要鉴权的路径
  const WHITE_LIST = ["/auth/callback", "/404", "/403"];

  if (WHITE_LIST.includes(to.path)) {
    return;
  }

  // 未登录 → 重定向到 OAuth2 授权端点
  if (!token) {
    const { buildAuthorizeUrl } = useAuth();
    const url = await buildAuthorizeUrl(to.fullPath);
    // 使用 navigateTo + external，Nuxt 会阻止当前页面渲染，不会闪烁 404
    return navigateTo(url, { external: true });
  }

  // 已登录但角色为空 → 拉取用户信息
  if (userStore.roles.length === 0) {
    try {
      await userStore.getUserInfo();
    } catch {
      userStore.resetToken();
      const { buildAuthorizeUrl } = useAuth();
      const url = await buildAuthorizeUrl(to.fullPath);
      return navigateTo(url, { external: true });
    }
  }

  // == 进阶 RBAC 权限守卫 ==
  // 若目标路由配置了 meta.permission，校验用户是否具备对应权限
  if (to.meta.permission) {
    const { hasPermission } = await import("@/utils/permission");
    if (!hasPermission(to.meta.permission as string | string[])) {
      // 越权访问，重定向回 403 页面
      return navigateTo("/403");
    }
  }
});
