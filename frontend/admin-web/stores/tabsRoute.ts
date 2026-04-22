import { defineStore } from "pinia";

export interface TabItem {
  path: string;
  title: string;
  closable: boolean;
}

/** 路径 → 标题 静态映射（用于自动推导 Tab 名称）*/
const ROUTE_TITLE_MAP: Record<string, string> = {
  // 平台管理
  "/admin": "工作台",
  "/admin/users": "用户管理",
  "/admin/roles": "角色与权限",
  "/admin/menus": "菜单管理",
  "/admin/tenants": "租户管理",
  "/admin/organizations": "组织架构",
  "/admin/sso": "SSO集成",
  "/admin/audit": "审计日志",
  "/admin/profile": "个人中心",
  // 档案管理系统
  "/archive": "档案工作台",
  "/archive/collection/transfer": "归档移交",
  "/archive/collection/receive": "接收登记",
  "/archive/collection/import": "批量导入",
  "/archive/collection/ledger": "收集台账",
  "/archive/organize/records": "档案著录",
  "/archive/organize/catalogs": "目录管理",
  "/archive/organize/digitize": "数字化加工",
  "/archive/organize/ledger": "整理台账",
  "/archive/storage/vault": "库房管理",
  "/archive/storage/inout": "出入库记录",
  "/archive/storage/detection": "四性检测",
  "/archive/storage/repair": "档案修复",
  "/archive/storage/ledger": "保管台账",
  "/archive/utilization/apply": "利用申请",
  "/archive/utilization/reading": "查阅登记",
  "/archive/utilization/borrow": "借阅管理",
  "/archive/utilization/copy": "复制申请",
  "/archive/utilization/certificate": "证明开具",
  "/archive/utilization/ledger": "利用台账",
  "/archive/appraisal/plan": "鉴定计划",
  "/archive/appraisal/review": "期限复查",
  "/archive/appraisal/evaluate": "鉴定工作",
  "/archive/appraisal/destroy-apply": "销毁申请",
  "/archive/appraisal/destroy-approve": "销毁审批",
  "/archive/appraisal/destroy-exec": "销毁执行",
  "/archive/appraisal/ledger": "鉴定台账",
  "/archive/research/project": "编研项目",
  "/archive/research/compilation": "专题汇编",
  "/archive/research/stats": "档案统计",
  "/archive/research/annual": "年报管理",
  "/archive/settings/fonds": "全宗管理",
  "/archive/settings/categories": "档案门类",
  "/archive/settings/norules": "档号规则",
  "/archive/settings/retention": "保管期限表",
  "/archive/settings/metadata": "元数据方案",
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
