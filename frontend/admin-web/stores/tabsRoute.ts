import { defineStore } from "pinia";

export interface TabItem {
  path: string;
  title: string;
  closable: boolean;
}

/** 路径 → 标题 静态映射（用于自动推导 Tab 名称）*/
const ROUTE_TITLE_MAP: Record<string, string> = {
  "/admin": "工作台",
  "/admin/users": "用户管理",
  "/admin/roles": "角色与权限",
  "/admin/menus": "菜单管理",
  "/admin/tenants": "租户管理",
  "/admin/organizations": "组织架构",
  "/admin/sso": "SSO集成",
  "/admin/audit": "审计日志",
  "/admin/profile": "个人中心",
  "/admin/repository": "档案库",
  "/admin/repository/fonds": "全宗管理",
  "/admin/collection": "档案采集",
  "/admin/preservation": "档案保管",
  "/admin/utilization": "档案利用",
  "/admin/ai": "智能助手",
};

const HOME_PATH = "/admin";

function getTabTitle(path: string): string {
  // Strip query string for lookup
  const cleanPath = path.split("?")[0] ?? path;
  return ROUTE_TITLE_MAP[cleanPath] ?? cleanPath.split("/").pop() ?? path;
}

export const useTabsRouteStore = defineStore("tabsRoute", {
  state: (): { tabs: TabItem[]; activeTab: string } => ({
    tabs: [
      {
        path: HOME_PATH,
        title: "工作台",
        closable: false,
      },
    ],
    activeTab: HOME_PATH,
  }),

  actions: {
    /** 导航到某个路径时调用，自动添加或激活对应 Tab */
    openTab(path: string, title?: string) {
      const existing = this.tabs.find((t) => t.path === path);
      if (!existing) {
        this.tabs.push({
          path,
          title: title ?? getTabTitle(path),
          closable: path !== HOME_PATH,
        });
      }
      this.activeTab = path;
    },

    /** 关闭指定 Tab，返回需要跳转的路径（若关闭的是当前激活 Tab）*/
    closeTab(path: string): string | null {
      const idx = this.tabs.findIndex((t) => t.path === path);
      if (idx === -1) return null;
      if (!this.tabs[idx]?.closable) return null;

      this.tabs = this.tabs.filter((t) => t.path !== path);

      if (this.activeTab === path) {
        // 优先激活左侧 Tab，否则右侧，否则 Home
        const next = this.tabs[idx - 1] ?? this.tabs[idx] ?? this.tabs[0];
        this.activeTab = next?.path ?? HOME_PATH;
        return this.activeTab;
      }
      return null;
    },

    /** 关闭除指定路径外的所有可关闭 Tab */
    closeOthers(path: string) {
      this.tabs = this.tabs.filter((t) => !t.closable || t.path === path);
      this.activeTab = path;
    },

    /** 关闭指定 Tab 右侧的所有可关闭 Tab */
    closeRight(path: string) {
      const idx = this.tabs.findIndex((t) => t.path === path);
      if (idx === -1) return;
      const rightClosable = this.tabs
        .slice(idx + 1)
        .filter((t) => t.closable)
        .map((t) => t.path);
      this.tabs = this.tabs.filter((t) => !rightClosable.includes(t.path));
      if (!this.tabs.find((t) => t.path === this.activeTab)) {
        this.activeTab = path;
      }
    },

    /** 关闭所有可关闭 Tab */
    closeAll() {
      this.tabs = this.tabs.filter((t) => !t.closable);
      this.activeTab = this.tabs[0]?.path ?? HOME_PATH;
    },

    setActive(path: string) {
      this.activeTab = path;
    },
  },
});
