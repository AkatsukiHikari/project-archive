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
              <NuxtPage />
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
import { Toaster } from "vue-sonner";
import { useTheme } from "@/hooks/useTheme";
import { useNaiveTheme } from "@/composables/useNaiveTheme";

const { currentTheme, initTheme } = useTheme();
const { naiveTheme, themeOverrides } = useNaiveTheme();

onMounted(() => {
  initTheme();
});
</script>
