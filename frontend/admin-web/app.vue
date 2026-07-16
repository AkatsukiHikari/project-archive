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
              <NuxtPage
                :keepalive="{ max: 20 }"
                :page-key="pageKey"
                :transition="{ name: 'page-fade', mode: 'out-in' }"
              />
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

<style>
/* 页面切换过渡：150ms 淡入，keep-alive 缓存不受影响 */
.page-fade-enter-active,
.page-fade-leave-active {
  transition: opacity 0.15s ease;
}
.page-fade-enter-from,
.page-fade-leave-to {
  opacity: 0;
}

/* 全局细滚动条（内容区/表格/弹层统一） */
*::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}
*::-webkit-scrollbar-track {
  background: transparent;
}
*::-webkit-scrollbar-thumb {
  background-color: var(--semi-color-fill-1);
  border-radius: 20px;
}
*::-webkit-scrollbar-thumb:hover {
  background-color: var(--semi-color-fill-2);
}
</style>
