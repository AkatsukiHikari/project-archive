<template>
  <AdminShell
    :options="menuOptions"
    title="档案管理系统"
    subtitle="SAMS · Archive"
    tabs-prefix="/archive"
    :tabs-extra-paths="['/ai', '/ai/catalog', '/ai/proofread', '/ai/knowledge', '/ai/ocr']"
    show-back-home
    content-class="px-6 py-3"
  >
    <slot />
  </AdminShell>
</template>

<script setup lang="ts">
import { computed, onMounted, watch } from "vue";
import { useRoute } from "vue-router";
import type { MenuOption } from "naive-ui";
import AdminShell from "@/components/layout/AdminShell.vue";
import { buildMenuOptions } from "@/components/layout/menuOptions";
import { useUserStore } from "@/stores/user";
import { useTabsRouteStore } from "@/stores/tabsRoute";

const route = useRoute();
const userStore = useUserStore();
const tabsStore = useTabsRouteStore();

// 确保档案子系统固定首页 Tab 存在（非关闭的 home tab）
tabsStore.ensureHome("/archive", "档案工作台");

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
    // 档案子系统页 + AI 对话助手（portal 级功能，复用档案工作区标签）
    if (!path.startsWith("/archive") && !path.startsWith("/ai")) return;
    const breadcrumbs = route.meta.breadcrumb as { name: string; path: string }[] | undefined;
    const title = breadcrumbs?.[breadcrumbs.length - 1]?.name;
    tabsStore.openTab(path, title);
  },
  { immediate: true },
);

// ─── 侧边栏菜单数据（仅 archive.* 前缀 + AI） ─────────────────────────────────
const menuOptions = computed<MenuOption[]>(() =>
  buildMenuOptions(
    userStore,
    (code) => code.startsWith("archive.") || code === "ai" || code.startsWith("ai:"),
  ),
);
</script>
