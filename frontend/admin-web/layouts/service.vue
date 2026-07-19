<template>
  <AdminShell
    :options="menuOptions"
    title="利用服务中心"
    subtitle="SAMS · Service"
    tabs-prefix="/service"
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

// 利用服务中心子系统固定首页 Tab
tabsStore.ensureHome("/service", "服务工作台");

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
    if (!path.startsWith("/service")) return;
    const breadcrumbs = route.meta.breadcrumb as { name: string; path: string }[] | undefined;
    const title = breadcrumbs?.[breadcrumbs.length - 1]?.name;
    tabsStore.openTab(path, title);
  },
  { immediate: true },
);

// ─── 侧边栏菜单（service:* 平铺，不再套子系统同名分组） ───────────────────────
const menuOptions = computed<MenuOption[]>(() =>
  buildMenuOptions(userStore, (code) => code.startsWith("service:")),
);
</script>
