<template>
  <!-- ═══ 侧边布局：左菜单 + 顶栏(面包屑+操作) + 页签 ═══ -->
  <div v-if="layout.mode === 'sidebar'" class="flex min-h-screen" style="overflow-x: hidden">
    <SidebarNav
      :options="options"
      :selected-key="selectedKey"
      :title="title"
      :subtitle="subtitle"
      :show-back-home="showBackHome"
      @select="onNavigate"
    />
    <div class="flex-none shrink-0" style="transition: width 0.3s ease" :style="{ width: asideWidth }" />

    <div class="flex flex-col min-h-screen flex-1 min-w-0" style="padding-top: 104px; background: var(--semi-color-bg-1)">
      <div class="fixed top-0 right-0 z-30" style="transition: left 0.3s ease" :style="{ left: asideWidth }">
        <SystemHeader />
        <TabsBar :prefix="tabsPrefix" :extra-paths="tabsExtraPaths" />
      </div>
      <main class="flex-1 w-full min-w-0 overflow-x-hidden" :class="contentClass">
        <slot />
      </main>
      <AppFooter />
    </div>
  </div>

  <!-- ═══ 顶部布局：Logo+横向菜单+操作区一行，内容通栏 ═══ -->
  <div v-else-if="layout.mode === 'topnav'" class="flex flex-col min-h-screen" style="overflow-x: hidden; background: var(--semi-color-bg-1)">
    <div class="fixed top-0 inset-x-0 z-40">
      <header
        class="h-14 flex items-center gap-4 px-4"
        style="background: var(--semi-color-bg-0); border-bottom: 1px solid var(--semi-color-border)"
      >
        <ShellLogo :title="title" :subtitle="subtitle" />
        <TopNav :options="options" :selected-key="selectedKey" @select="onNavigate" />
        <HeaderActions />
      </header>
      <TabsBar :prefix="tabsPrefix" :extra-paths="tabsExtraPaths" />
    </div>

    <div class="flex flex-col min-h-screen flex-1 min-w-0" style="padding-top: 104px">
      <main class="flex-1 w-full min-w-0 overflow-x-hidden" :class="contentClass">
        <slot />
      </main>
      <AppFooter />
    </div>
  </div>

  <!-- ═══ 混合布局：顶栏一级栏目 + 侧栏当前栏目二级菜单 ═══ -->
  <div v-else class="flex min-h-screen" style="overflow-x: hidden">
    <SidebarNav
      v-if="mixSideOptions.length"
      :options="mixSideOptions"
      :selected-key="selectedKey"
      :top="56"
      :show-logo="false"
      :show-back-home="showBackHome"
      @select="onNavigate"
    />
    <div
      v-if="mixSideOptions.length"
      class="flex-none shrink-0"
      style="transition: width 0.3s ease"
      :style="{ width: asideWidth }"
    />

    <div class="flex flex-col min-h-screen flex-1 min-w-0" style="padding-top: 104px; background: var(--semi-color-bg-1)">
      <!-- 顶栏：全宽，z 高于侧栏 -->
      <div class="fixed top-0 inset-x-0 z-50">
        <header
          class="h-14 flex items-center gap-4 px-4"
          style="background: var(--semi-color-bg-0); border-bottom: 1px solid var(--semi-color-border)"
        >
          <ShellLogo :title="title" :subtitle="subtitle" />
          <TopNav :options="mixTopOptions" :selected-key="mixActiveTopKey" @select="onMixTopSelect" />
          <HeaderActions />
        </header>
      </div>
      <!-- 页签：顶栏之下，避开侧栏 -->
      <div
        class="fixed z-30 right-0"
        style="top: 56px; transition: left 0.3s ease"
        :style="{ left: mixSideOptions.length ? asideWidth : '0px' }"
      >
        <TabsBar :prefix="tabsPrefix" :extra-paths="tabsExtraPaths" />
      </div>

      <main class="flex-1 w-full min-w-0 overflow-x-hidden" :class="contentClass">
        <slot />
      </main>
      <AppFooter />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import type { MenuOption } from "naive-ui";
import SidebarNav from "./SidebarNav.vue";
import TopNav from "./TopNav.vue";
import SystemHeader from "./SystemHeader.vue";
import TabsBar from "./TabsBar.vue";
import AppFooter from "./AppFooter.vue";
import ShellLogo from "./ShellLogo.vue";
import { findTopKeyByPath, firstLeafPath } from "./menuOptions";
import { useLayoutStore } from "@/stores/layout";

const props = withDefaults(
  defineProps<{
    options: MenuOption[];
    title: string;
    subtitle: string;
    tabsPrefix: string;
    tabsExtraPaths?: string[];
    showBackHome?: boolean;
    contentClass?: string;
  }>(),
  { tabsExtraPaths: () => [], showBackHome: false, contentClass: "px-6 py-3" },
);

const route = useRoute();
const router = useRouter();
const layout = useLayoutStore();

const asideWidth = computed(() => (layout.collapsed ? "64px" : "240px"));
const selectedKey = computed(() => route.path);

function onNavigate(key: string) {
  if (key.startsWith("/")) router.push(key);
}

// ── 混合布局：一级栏目在顶栏，二级在侧栏 ─────────────────────────────────────
const mixTopOptions = computed<MenuOption[]>(() =>
  props.options.map((o) => ({ key: o.key, label: o.label, icon: o.icon })),
);

// 当前路由所属的一级栏目；路由不在菜单里（如详情页）时保持上一次的栏目
const mixActiveTopKey = ref<string | null>(null);
watch(
  () => [route.path, props.options] as const,
  ([path, options]) => {
    const hit = findTopKeyByPath(options, path);
    if (hit) {
      mixActiveTopKey.value = hit;
    } else if (!mixActiveTopKey.value && options.length) {
      mixActiveTopKey.value = String(options[0].key);
    }
  },
  { immediate: true, deep: false },
);

const mixSideOptions = computed<MenuOption[]>(() => {
  const top = props.options.find((o) => String(o.key) === mixActiveTopKey.value);
  return (top?.children as MenuOption[] | undefined) ?? [];
});

function onMixTopSelect(key: string) {
  mixActiveTopKey.value = key;
  if (key.startsWith("/")) {
    router.push(key);
    return;
  }
  const top = props.options.find((o) => String(o.key) === key);
  const leaf = top ? firstLeafPath(top) : null;
  if (leaf) router.push(leaf);
}
</script>
