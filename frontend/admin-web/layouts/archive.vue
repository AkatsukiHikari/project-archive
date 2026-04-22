<template>
  <div class="flex min-h-screen" style="overflow-x:hidden">

    <!-- ── 左侧固定侧边栏 ─────────────────────────────────────── -->
    <aside
      class="fixed inset-y-0 left-0 z-40 flex flex-col"
      style="transition:width 0.3s ease"
      :style="{
        width: isCollapsed ? '64px' : '240px',
        background: 'var(--semi-color-bg-0)',
        borderRight: '1px solid var(--semi-color-border)',
      }"
    >
      <!-- Logo -->
      <div
        class="flex items-center shrink-0 overflow-hidden transition-all duration-300"
        :style="{ padding: isCollapsed ? '12px 14px' : '12px 14px', height: '56px' }"
      >
        <LogoIcon :size="28" class="shrink-0" />
        <Transition name="logo-text">
          <div v-if="!isCollapsed" class="ml-2.5 overflow-hidden">
            <div class="text-[13px] font-bold leading-tight whitespace-nowrap" style="color: var(--semi-color-text-0)">
              档案管理系统
            </div>
            <div class="text-[9px] tracking-widest uppercase mt-0.5" style="color: var(--semi-color-text-2)">
              SAMS · Archive
            </div>
          </div>
        </Transition>
      </div>

      <!-- Nav menu -->
      <div class="flex-1 overflow-y-auto custom-scrollbar">
        <NMenu
          :options="menuOptions"
          :collapsed="isCollapsed"
          :collapsed-width="64"
          :collapsed-icon-size="20"
          :indent="18"
          :value="selectedKey"
          :expanded-keys="expandedKeys"
          @update:value="onMenuSelect"
          @update:expanded-keys="expandedKeys = $event"
        />
      </div>

      <!-- 返回主界面 -->
      <div
        class="shrink-0 border-t"
        style="border-color: var(--semi-color-border)"
      >
        <button
          class="w-full flex items-center gap-2 h-10 px-4 transition-colors cursor-pointer hover:bg-[var(--semi-color-fill-0)]"
          :class="isCollapsed ? 'justify-center' : 'justify-start'"
          @click="router.push('/')"
        >
          <Icon
            name="heroicons:home"
            class="w-4 h-4 shrink-0"
            style="color: var(--semi-color-text-2)"
          />
          <span v-if="!isCollapsed" class="text-xs" style="color: var(--semi-color-text-2)">返回主界面</span>
        </button>
      </div>

      <!-- 折叠按钮 -->
      <div
        class="shrink-0 border-t"
        style="border-color: var(--semi-color-border)"
      >
        <button
          class="w-full flex items-center justify-center h-10 transition-colors cursor-pointer hover:bg-[var(--semi-color-fill-0)]"
          @click="isCollapsed = !isCollapsed"
        >
          <Icon
            :name="isCollapsed ? 'heroicons:chevron-right' : 'heroicons:chevron-left'"
            class="w-4 h-4"
            style="color: var(--semi-color-text-2)"
          />
        </button>
      </div>
    </aside>

    <!-- ── 占位块 ──────────────────────────────────────────────── -->
    <div
      class="flex-none shrink-0"
      style="transition:width 0.3s ease"
      :style="{ width: isCollapsed ? '64px' : '240px' }"
    />

    <!-- ── 右侧主体区域 ─────────────────────────────────────────── -->
    <div
      class="flex flex-col min-h-screen flex-1 min-w-0"
      :style="{
        paddingTop: '104px',
        background: 'var(--semi-color-bg-1)',
      }"
    >
      <!-- 顶部固定栏 -->
      <div
        class="fixed top-0 right-0 z-30"
        style="transition:left 0.3s ease"
        :style="{ left: isCollapsed ? '64px' : '240px' }"
      >
        <SystemHeader />
        <TabsBar />
      </div>

      <!-- 内容区 -->
      <main class="p-6 flex-1 w-full min-w-0 overflow-x-hidden">
        <slot />
      </main>

      <!-- 底部 -->
      <AppFooter />
    </div>

  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, h, onMounted } from "vue";
import { useRouter, useRoute } from "vue-router";
import { NMenu, type MenuOption } from "naive-ui";
import * as HeroIcons from "@heroicons/vue/24/outline";
import type { Component } from "vue";
import SystemHeader from "@/components/layout/SystemHeader.vue";
import TabsBar from "@/components/layout/TabsBar.vue";
import AppFooter from "@/components/layout/AppFooter.vue";
import LogoIcon from "@/components/common/LogoIcon.vue";
import { useUserStore } from "@/stores/user";
import { useTabsRouteStore } from "@/stores/tabsRoute";

const router = useRouter();
const route = useRoute();
const userStore = useUserStore();
const tabsStore = useTabsRouteStore();

// ─── 刷新后补全用户信息 ────────────────────────────────────────────────────────
onMounted(async () => {
  if (userStore.token && !userStore.userInfo) {
    try {
      await userStore.getUserInfo();
    } catch {
      // 拉取失败由 auth 中间件统一处理跳转
    }
  }
});

// ─── 路由变化时自动开标签页 ───────────────────────────────────────────────────
watch(
  () => route.path,
  (path) => {
    if (!path.startsWith("/archive")) return;
    const breadcrumbs = route.meta.breadcrumb as { name: string; path: string }[] | undefined;
    const title = breadcrumbs?.[breadcrumbs.length - 1]?.name;
    tabsStore.openTab(path, title);
  },
  { immediate: true },
);

// ─── 图标解析（heroicons:xxx → Vue 组件） ────────────────────────────────────
function resolveHeroIcon(iconName?: string): Component | undefined {
  if (!iconName) return undefined;
  const name = iconName.startsWith("heroicons:") ? iconName.slice(10) : iconName;
  const compName =
    name
      .split("-")
      .map((s) => s.charAt(0).toUpperCase() + s.slice(1))
      .join("") + "Icon";
  return (HeroIcons as Record<string, Component>)[compName];
}

function makeMenuIcon(iconName?: string): MenuOption["icon"] {
  const Comp = resolveHeroIcon(iconName);
  if (Comp) return () => h(Comp, { style: "width:18px;height:18px;display:block" });
  return () =>
    h("span", {
      style:
        "display:inline-block;width:6px;height:6px;border-radius:50%;background:currentColor;opacity:0.4;flex-shrink:0",
    });
}

// ─── 后端菜单节点类型 ──────────────────────────────────────────────────────────
interface RawMenuNode {
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

// ─── 菜单树转 NMenu options ────────────────────────────────────────────────────
function mapToMenuOptions(menus: RawMenuNode[]): MenuOption[] {
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

// ─── 侧边栏菜单数据（仅 archive.* 前缀） ───────────────────────────────────────
const menuOptions = computed<MenuOption[]>(() => {
  if (!userStore.userInfo || !userStore.roles.length) return [];

  const allMenus = userStore.userInfo.roles.flatMap((r) => r.menus || []);
  const uniqueMenus = Array.from(new Map(allMenus.map((m) => [m.id, m])).values());

  const filtered = uniqueMenus
    .filter(
      (m) =>
        m.type !== "BUTTON" &&
        m.is_visible &&
        m.code.startsWith("archive."),
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
});

// ─── 当前路由高亮 ──────────────────────────────────────────────────────────────
const selectedKey = computed(() => route.path);

// ─── 展开状态管理 ─────────────────────────────────────────────────────────────
const expandedKeys = ref<string[]>([]);

watch(
  menuOptions,
  (opts) => {
    if (expandedKeys.value.length === 0) {
      expandedKeys.value = opts
        .filter((o) => Array.isArray(o.children) && o.children.length > 0)
        .map((o) => String(o.key));
    }
  },
  { immediate: true },
);

// ─── 菜单选中跳转 ──────────────────────────────────────────────────────────────
function onMenuSelect(key: string) {
  if (key.startsWith("/")) {
    router.push(key);
  }
}

// ─── 侧边栏折叠 ───────────────────────────────────────────────────────────────
const isCollapsed = ref(false);
</script>

<style scoped>
.custom-scrollbar::-webkit-scrollbar { width: 4px; }
.custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
.custom-scrollbar::-webkit-scrollbar-thumb {
  background-color: var(--semi-color-fill-1);
  border-radius: 20px;
}

.logo-text-enter-active,
.logo-text-leave-active { transition: opacity 0.2s, transform 0.2s; }
.logo-text-enter-from,
.logo-text-leave-to { opacity: 0; transform: translateX(-6px); }
</style>
