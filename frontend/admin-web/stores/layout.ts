/**
 * 后台外壳布局偏好（档案子系统 / 系统管理共用）
 * - mode：sidebar 侧边布局 | topnav 顶部布局 | mix 混合布局
 * - sidebarDark：侧栏深色
 * - collapsed：侧栏折叠
 * 全部持久化 localStorage，仅本浏览器生效。
 */
import { defineStore } from "pinia";

export type LayoutMode = "sidebar" | "topnav" | "mix";

const MODE_KEY = "sams_layout_mode";
const DARK_KEY = "sams_sidebar_dark";
const COLLAPSED_KEY = "sams_sidebar_collapsed";

function readMode(): LayoutMode {
  if (typeof window === "undefined") return "sidebar";
  const v = localStorage.getItem(MODE_KEY);
  return v === "topnav" || v === "mix" ? v : "sidebar";
}

function readBool(key: string): boolean {
  if (typeof window === "undefined") return false;
  return localStorage.getItem(key) === "1";
}

export const useLayoutStore = defineStore("layout", {
  state: () => ({
    mode: readMode(),
    sidebarDark: readBool(DARK_KEY),
    collapsed: readBool(COLLAPSED_KEY),
  }),
  actions: {
    setMode(mode: LayoutMode) {
      this.mode = mode;
      localStorage.setItem(MODE_KEY, mode);
    },
    setSidebarDark(dark: boolean) {
      this.sidebarDark = dark;
      localStorage.setItem(DARK_KEY, dark ? "1" : "0");
    },
    toggleCollapsed() {
      this.collapsed = !this.collapsed;
      localStorage.setItem(COLLAPSED_KEY, this.collapsed ? "1" : "0");
    },
  },
});
