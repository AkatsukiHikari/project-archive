<template>
  <NConfigProvider
    :theme="naiveTheme"
    :theme-overrides="themeOverrides"
    :locale="zhCN"
    :date-locale="dateZhCN"
  >
    <NMessageProvider>
      <NDialogProvider>
        <NNotificationProvider>
          <div :data-theme="currentTheme">
            <NuxtLayout>
              <NuxtPage :keepalive="{ max: 20 }" :page-key="pageKey" />
            </NuxtLayout>
            <Toaster position="top-right" rich-colors />
          </div>
        </NNotificationProvider>
      </NDialogProvider>
    </NMessageProvider>
  </NConfigProvider>
</template>

<script setup lang="ts">
import {
  NConfigProvider,
  NMessageProvider,
  NDialogProvider,
  NNotificationProvider,
  zhCN,
  dateZhCN,
} from "naive-ui";
import type { RouteLocationNormalizedLoaded } from "vue-router";
import { Toaster } from "vue-sonner";
import { useTheme } from "@/hooks/useTheme";
import { useNaiveTheme } from "@/composables/useNaiveTheme";
import { useTabsRouteStore } from "@/stores/tabsRoute";

const { currentTheme, initTheme } = useTheme();
const { naiveTheme, themeOverrides } = useNaiveTheme();

// keep-alive 页面 key：路径 + Tab 代次号（Tab 开着=同 key 命中缓存保活；关闭后重开=新 key 干净页）
const tabsStore = useTabsRouteStore();
const pageKey = (route: RouteLocationNormalizedLoaded) => tabsStore.pageKey(route.path);

onMounted(() => {
  initTheme();
});
</script>
