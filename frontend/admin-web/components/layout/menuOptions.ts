/**
 * 后台菜单构建工具（archive / admin 两个外壳共用）
 * 后端菜单树 → Naive UI MenuOption；heroicons:xxx 图标名 → 组件。
 */
import { h } from "vue";
import type { Component } from "vue";
import type { MenuOption } from "naive-ui";
import * as HeroIcons from "@heroicons/vue/24/outline";
import type { useUserStore } from "@/stores/user";

export interface RawMenuNode {
  id: string;
  name: string;
  code: string;
  type: string;
  path?: string | null;
  icon?: string;
  parent_id?: string | null;
  sort_order: number;
  is_visible: boolean;
  children: RawMenuNode[];
}

export function resolveHeroIcon(iconName?: string): Component | undefined {
  if (!iconName) return undefined;
  const name = iconName.startsWith("heroicons:") ? iconName.slice(10) : iconName;
  const compName =
    name
      .split("-")
      .map((s) => s.charAt(0).toUpperCase() + s.slice(1))
      .join("") + "Icon";
  return (HeroIcons as Record<string, Component>)[compName];
}

export function makeMenuIcon(iconName?: string): MenuOption["icon"] {
  const Comp = resolveHeroIcon(iconName);
  if (Comp) return () => h(Comp, { style: "width:18px;height:18px;display:block" });
  // 图标未配置时显示小圆点，折叠态下仍可辨识
  return () =>
    h("span", {
      style:
        "display:inline-block;width:6px;height:6px;border-radius:50%;background:currentColor;opacity:0.4;flex-shrink:0",
    });
}

export function mapToMenuOptions(menus: RawMenuNode[]): MenuOption[] {
  return menus.map((m) => {
    const option: MenuOption = {
      key: m.path || m.id,
      label: m.name,
      icon: makeMenuIcon(m.icon),
    };
    if (m.children.length > 0) {
      option.children = mapToMenuOptions(m.children);
    }
    return option;
  });
}

/** 用户全部菜单 → 按 code 过滤 → 树 → MenuOption[] */
export function buildMenuOptions(
  userStore: ReturnType<typeof useUserStore>,
  codeFilter: (code: string) => boolean,
): MenuOption[] {
  if (!userStore.userInfo || !userStore.roles.length) return [];

  const allMenus = userStore.userInfo.roles.flatMap((r) => r.menus || []);
  const uniqueMenus = Array.from(new Map(allMenus.map((m) => [m.id, m])).values());

  const filtered = uniqueMenus
    .filter(
      (m) =>
        m.type !== "BUTTON" &&
        m.is_visible &&
        (m as { is_deleted?: boolean }).is_deleted !== true &&
        codeFilter(m.code),
    )
    .sort((a, b) => a.sort_order - b.sort_order);

  const menuMap = new Map<string, RawMenuNode>();
  filtered.forEach((m) => menuMap.set(m.id, { ...m, children: [] } as RawMenuNode));

  const tree: RawMenuNode[] = [];
  filtered.forEach((m) => {
    if (m.parent_id && menuMap.has(m.parent_id)) {
      menuMap.get(m.parent_id)!.children.push(menuMap.get(m.id)!);
    } else {
      tree.push(menuMap.get(m.id)!);
    }
  });

  return mapToMenuOptions(tree);
}

/** 树里第一个可跳转叶子的路径（混合布局点一级栏目时用） */
export function firstLeafPath(option: MenuOption): string | null {
  const key = String(option.key ?? "");
  if (!option.children?.length) return key.startsWith("/") ? key : null;
  for (const child of option.children) {
    const p = firstLeafPath(child as MenuOption);
    if (p) return p;
  }
  return null;
}

/** 当前路由属于哪个一级栏目（混合布局顶栏高亮/侧栏内容用） */
export function findTopKeyByPath(options: MenuOption[], path: string): string | null {
  const contains = (opt: MenuOption): boolean => {
    const key = String(opt.key ?? "");
    if (key === path) return true;
    return (opt.children ?? []).some((c) => contains(c as MenuOption));
  };
  for (const top of options) {
    if (contains(top)) return String(top.key);
  }
  return null;
}
