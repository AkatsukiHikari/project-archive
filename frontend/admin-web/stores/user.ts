import { defineStore } from 'pinia';
import type { UserInfo } from '@/types/api';

/**
 * 用户状态管理 Store
 */
export const useUserStore = defineStore('user', {
  state: () => ({
    /** 访问令牌 */
    token: useCookie<string>('access_token').value || '',
    /** 用户详细信息 */
    userInfo: null as UserInfo | null,
    /** 当前角色列表 */
    roles: [] as string[],
  }),
  
  actions: {
    /**
     * 设置 Token
     * 同时更新 Cookie 以便持久化
     */
    setToken(token: string) {
      this.token = token;
      // 设置 Cookie，过期时间与后端 Token 一致或略长（这里默认 7 天）
      const cookie = useCookie('access_token', { maxAge: 60 * 60 * 24 * 7 });
      cookie.value = token;
    },

    /**
     * 设置用户信息
     */
    setUserInfo(info: UserInfo) {
      this.userInfo = info;
      this.roles = info.roles || [];
    },

    /**
     * 重置 Token 和用户信息（注销时调用）
     */
    resetToken() {
      this.token = '';
      this.userInfo = null;
      this.roles = [];
      const cookie = useCookie('access_token');
      cookie.value = null;
    },

    /**
     * 获取用户信息 (当页面刷新仅有 Token 时调用)
     * TODO: 实际对接后端 /auth/me 接口
     */
    async getUserInfo() {
      // 模拟请求
      return new Promise<void>((resolve) => {
        // 这里应该调用 http.get('/auth/me')
        // 暂时 mock
        if (this.token) {
          this.setUserInfo({
            id: 'mock-id',
            username: 'admin',
            email: 'admin@local.com',
            roles: ['admin']
          });
        }
        resolve();
      });
    }
  },
});