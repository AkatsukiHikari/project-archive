<template>
  <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
    <NuxtLink
      v-for="app in apps"
      :key="app.name"
      :to="app.href"
      class="block app-card-link"
      style="text-decoration: none; color: inherit;"
    >
      <Card
        :shadows="'hover'"
        :header-line="false"
        :body-style="{ padding: '20px', height: '100%' }"
        class="app-card h-full transition-all duration-200"
      >
        <div class="flex flex-col h-full">
          <!-- 应用图标 -->
          <div
            class="w-11 h-11 rounded-xl flex items-center justify-center mb-4 shrink-0"
            :class="app.iconBg"
          >
            <Icon :name="app.icon" class="w-5 h-5" :class="app.iconColor" />
          </div>

          <!-- 应用名称 -->
          <div
            class="text-[14px] font-semibold mb-1.5 transition-colors duration-150"
            :class="app.hoverColor"
            style="color: var(--semi-color-text-0);"
          >
            {{ app.name }}
          </div>

          <!-- 应用描述 -->
          <div
            class="text-[12px] leading-relaxed line-clamp-2"
            style="color: var(--semi-color-text-2);"
          >
            {{ app.description }}
          </div>

          <!-- 箭头指示 -->
          <div class="mt-auto pt-3 flex items-center gap-1 app-card-arrow">
            <span class="text-[11px] font-medium" style="color: var(--semi-color-primary);">
              进入应用
            </span>
            <Icon name="heroicons:arrow-right" class="w-3 h-3" style="color: var(--semi-color-primary);" />
          </div>
        </div>
      </Card>
    </NuxtLink>
  </div>
</template>

<script setup lang="ts">
import { Card } from "@kousum/semi-ui-vue";

interface AppItem {
  name: string;
  description: string;
  icon: string;
  iconBg: string;
  iconColor: string;
  hoverColor: string;
  href: string;
}

defineProps<{
  apps: AppItem[];
}>();
</script>

<style scoped>
/* 箭头默认隐藏，hover 时显示 */
.app-card-arrow {
  opacity: 0;
  transform: translateX(-4px);
  transition: opacity 0.2s ease, transform 0.2s ease;
}

.app-card-link:hover .app-card-arrow {
  opacity: 1;
  transform: translateX(0);
}

/* hover 时给 Semi Card 添加左侧主色 border 指示 */
.app-card-link:hover :deep(.semi-card) {
  border-left: 2px solid var(--semi-color-primary) !important;
}
</style>
