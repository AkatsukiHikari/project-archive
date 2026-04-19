<template>
  <div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
    <NuxtLink
      v-for="app in apps"
      :key="app.name"
      :to="app.href"
      class="block group app-card-link"
      style="text-decoration:none;color:inherit"
    >
      <div
        class="app-card h-full rounded-xl border p-5 flex flex-col transition-all duration-200 cursor-pointer"
        style="background:var(--semi-color-bg-0);border-color:var(--semi-color-border)"
      >
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
          style="color:var(--semi-color-text-0)"
        >
          {{ app.name }}
        </div>

        <!-- 应用描述 -->
        <div class="text-[12px] leading-relaxed line-clamp-2" style="color:var(--semi-color-text-2)">
          {{ app.description }}
        </div>

        <!-- 箭头指示 -->
        <div class="mt-auto pt-3 flex items-center gap-1 app-card-arrow">
          <span class="text-[11px] font-medium" style="color:var(--semi-color-primary)">进入应用</span>
          <Icon name="heroicons:arrow-right" class="w-3 h-3" style="color:var(--semi-color-primary)" />
        </div>
      </div>
    </NuxtLink>
  </div>
</template>

<script setup lang="ts">
interface AppItem {
  name: string;
  description: string;
  icon: string;
  iconBg: string;
  iconColor: string;
  hoverColor: string;
  href: string;
}

defineProps<{ apps: AppItem[] }>();
</script>

<style scoped>
.app-card-arrow {
  opacity: 0;
  transform: translateX(-4px);
  transition: opacity 0.2s ease, transform 0.2s ease;
}
.app-card-link:hover .app-card-arrow {
  opacity: 1;
  transform: translateX(0);
}
.app-card:hover {
  border-left: 2px solid var(--semi-color-primary);
  box-shadow: 0 4px 12px oklch(var(--bc) / 0.08);
}
</style>
