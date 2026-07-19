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
  "/archive/reader": "原文阅览",
  "/archive/organize/records": "档案著录",
  "/archive/organize/catalogs": "目录管理",
  "/archive/storage/vault": "库房管理",
  "/archive/storage/inout": "出入库记录",
  "/archive/storage/detection": "四性检测",
  "/archive/storage/repair": "档案修复",
  "/archive/storage/ledger": "保管台账",
  "/service/apply": "利用申请",
  "/service/kiosk-apps": "自助机申请",
  "/service/reading": "档案查询",
  "/service/borrow": "借阅管理",
  "/service/copy": "复制申请",
  "/service/certificate": "证明开具",
  "/service/ledger": "利用台账",
  "/archive/appraisal/plan": "鉴定计划",
  "/archive/appraisal/review": "鉴定审核",
  "/archive/appraisal/evaluate": "鉴定工作",
  "/archive/appraisal/standards": "鉴定标准",
  "/archive/appraisal/destroy-apply": "销毁申请",
  "/archive/appraisal/destroy-approve": "销毁审批",
  "/archive/appraisal/destroy-exec": "销毁执行",
  "/archive/appraisal/ledger": "鉴定台账",
  "/archive/statistics/overview": "综合统计",
  "/archive/statistics/cockpit": "大屏驾驶舱",
  "/archive/statistics/annual": "年度报表",
  "/archive/research/project": "编研项目",
  "/archive/research/compilation": "编研成果",
  "/archive/research/template": "编研模板",
  "/ai": "档案智能问答",
  "/service": "服务工作台",
  "/ai/catalog": "智能著录",
  "/ai/proofread": "智能校对",
  "/ai/knowledge": "AI 知识库",
  "/ai/ocr": "OCR 任务",
  "/archive/settings/fonds": "全宗管理",
  "/archive/settings/categories": "档案门类",
  "/archive/settings/norules": "档号规则",
  "/archive/settings/retention": "保管期限表",
  "/archive/settings/metadata": "元数据方案",
};

export function getTabTitle(path: string): string {
  const cleanPath = path.split("?")[0] ?? path;
  return ROUTE_TITLE_MAP[cleanPath] ?? cleanPath.split("/").filter(Boolean).pop() ?? path;
}

export const useTabsRouteStore = defineStore("tabsRoute", {
  state: (): { tabs: TabItem[]; activeTab: string; generation: Record<string, number> } => ({
    tabs: [
      { path: "/admin", title: "工作台", closable: false },
    ],
    activeTab: "/admin",
    // 每个路径的"代次号"：关闭 Tab 时 +1，使其 keep-alive 缓存失效（重开是干净新页）
    generation: {},
  }),

  actions: {
    /** keep-alive 用的页面 key：路径 + 代次号 */
    pageKey(path: string): string {
      return `${path}#${this.generation[path] ?? 0}`;
    },

    /** 关闭这些路径时 +1 代次，丢弃它们的 keep-alive 缓存 */
    _bumpGen(paths: string[]) {
      for (const p of paths) this.generation[p] = (this.generation[p] ?? 0) + 1;
    },
    /**
     * 确保某路径对应的 Home 标签页存在且不可关闭。
     * 每个子系统在其 layout 挂载时调用一次，保证各子系统有独立的固定首页标签。
     */
    ensureHome(path: string, title?: string) {
      const existing = this.tabs.find((t) => t.path === path);
      if (!existing) {
        // 插入到 tabs 最前面（所有可关闭 tab 之前）
        const firstClosableIdx = this.tabs.findIndex((t) => t.closable);
        const insertAt = firstClosableIdx === -1 ? this.tabs.length : firstClosableIdx;
        this.tabs.splice(insertAt, 0, {
          path,
          title: title ?? getTabTitle(path),
          closable: false,
        });
      } else if (existing.closable) {
        // 如果之前被意外标记为可关闭，修正它
        existing.closable = false;
      }
    },

    /** 导航到某个路径时调用，自动添加或激活对应 Tab */
    openTab(path: string, title?: string) {
      const existing = this.tabs.find((t) => t.path === path);
      if (!existing) {
        this.tabs.push({
          path,
          title: title ?? getTabTitle(path),
          // 非关闭判断：如果该 path 已经被 ensureHome 注册为 home，则不可关闭
          closable: !this.tabs.some((t) => t.path === path && !t.closable),
        });
      }
      this.activeTab = path;
    },

    /** 关闭指定 Tab，返回需要跳转的路径（若关闭的是当前激活 Tab）*/
    closeTab(path: string): string | null {
      const idx = this.tabs.findIndex((t) => t.path === path);
      if (idx === -1) return null;
      if (!this.tabs[idx]?.closable) return null;

      this._bumpGen([path]);
      this.tabs = this.tabs.filter((t) => t.path !== path);

      if (this.activeTab === path) {
        const next = this.tabs[idx - 1] ?? this.tabs[idx] ?? this.tabs[0];
        this.activeTab = next?.path ?? "/admin";
        return this.activeTab;
      }
      return null;
    },

    /** 关闭除指定路径外的本子系统所有可关闭 Tab */
    closeOthers(path: string) {
      // 找出 path 属于哪个子系统（取第一个路径段作为前缀）
      const prefix = "/" + (path.split("/")[1] ?? "");
      this._bumpGen(
        this.tabs
          .filter((t) => t.closable && t.path !== path && t.path.startsWith(prefix))
          .map((t) => t.path),
      );
      this.tabs = this.tabs.filter(
        (t) => !t.closable || t.path === path || !t.path.startsWith(prefix),
      );
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
      this._bumpGen(rightClosable);
      this.tabs = this.tabs.filter((t) => !rightClosable.includes(t.path));
      if (!this.tabs.find((t) => t.path === this.activeTab)) {
        this.activeTab = path;
      }
    },

    /** 关闭本子系统所有可关闭 Tab */
    closeAll() {
      this._bumpGen(this.tabs.filter((t) => t.closable).map((t) => t.path));
      this.tabs = this.tabs.filter((t) => !t.closable);
      this.activeTab = this.tabs[0]?.path ?? "/admin";
    },

    setActive(path: string) {
      this.activeTab = path;
    },
  },
});
