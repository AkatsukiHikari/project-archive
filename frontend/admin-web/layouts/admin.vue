<template>
  <AdminShell
    :options="menuOptions"
    title="智慧档案平台"
    subtitle="SAMS · Enterprise"
    tabs-prefix="/admin"
    content-class="p-6"
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
    if (!path.startsWith("/admin")) return;
    const breadcrumbs = route.meta.breadcrumb as { name: string; path: string }[] | undefined;
    const title = breadcrumbs?.[breadcrumbs.length - 1]?.name;
    tabsStore.openTab(path, title);
  },
  { immediate: true },
);

// ─── 侧边栏菜单数据（platform / security 前缀） ────────────────────────────────
const ADMIN_PREFIXES = ["platform", "security"];

const menuOptions = computed<MenuOption[]>(() =>
  buildMenuOptions(userStore, (code) =>
    ADMIN_PREFIXES.some((prefix) => code.startsWith(prefix)),
  ),
);
</script>
