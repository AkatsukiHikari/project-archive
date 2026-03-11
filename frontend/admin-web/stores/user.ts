import { defineStore } from "pinia";
import type { UserInfo } from "@/types/api";
import { UserAPI } from "@/api/iam";

/**
 * 用户状态管理 Store
 */
export const useUserStore = defineStore("user", {
  state: () => ({
    /** 访问令牌 */
    token: useCookie<string>("access_token").value || "",
    /** 用户详细信息 */
    userInfo: null as UserInfo | null,
    /** 角色编码列表（供权限判断使用） */
    roles: [] as string[],
  }),

  actions: {
    /**
     * 设置 Token，同步写入 Cookie（7天过期）
     */
    setToken(token: string) {
      this.token = token;
      const cookie = useCookie("access_token", { maxAge: 60 * 60 * 24 * 7 });
      cookie.value = token;
    },

    /**
     * 设置用户信息，同步派生 roles 角色码列表
     */
    setUserInfo(info: UserInfo) {
      this.userInfo = info;
      // 从 roles 对象数组中提取 code 字段，供中间件/权限判断使用
      this.roles = info.roles?.map((r) => r.code) ?? [];
    },

    /**
     * 重置 Token 和用户信息（注销时调用）
     */
    resetToken() {
      this.token = "";
      this.userInfo = null;
      this.roles = [];
      const cookie = useCookie("access_token");
      cookie.value = null;
    },

    /**
     * 从后端拉取当前用户信息并写入 Store。
     * 两处调用：
     *   1. OAuth2 callback 换完 token 后立即调用
     *   2. 路由守卫：有 token 但页面刷新导致 Pinia 丢失时调用
     */
    async getUserInfo(): Promise<void> {
      if (!this.token) return;
      const res = await UserAPI.getProfile();
      const user = res.data;
      // 将后端 User 对象映射为 store 的 UserInfo 格式
      this.setUserInfo({
        id: user.id,
        username: user.username,
        email: user.email,
        full_name: user.full_name,
        avatar: user.avatar,
        phone: user.phone,
        job_title: user.job_title,
        location: user.location,
        bio: user.bio,
        is_active: user.is_active,
        tenant_id: user.tenant_id,
        org_id: user.org_id,
        last_login_time: user.last_login_time,
        create_time: user.create_time,
        roles:
          user.roles?.map((r) => ({
            id: r.id,
            name: r.name,
            code: r.code,
            description: r.description,
          })) ?? [],
        roleCodes: user.roles?.map((r) => r.code) ?? [],
      });
    },
  },
});
