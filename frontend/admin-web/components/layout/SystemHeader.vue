<template>
  <header
    class="h-14 border-b flex items-center justify-between px-5 z-10 w-full"
    style="background: var(--semi-color-bg-0); border-color: var(--semi-color-border)"
  >
    <!-- 左侧：面包屑 -->
    <div class="flex items-center gap-2 min-w-0">
      <NBreadcrumb>
        <NBreadcrumbItem>
          <NuxtLink
            to="/"
            class="flex items-center gap-1 transition-colors hover:text-[var(--semi-color-primary)]"
          >
            <HomeIcon class="w-3.5 h-3.5" />
            首页
          </NuxtLink>
        </NBreadcrumbItem>
        <NBreadcrumbItem v-for="(item, index) in breadcrumbs" :key="index">
          <template v-if="index === breadcrumbs.length - 1">
            <span class="font-semibold truncate max-w-[200px]">{{ item.name }}</span>
          </template>
          <template v-else>
            <NuxtLink
              :to="item.path"
              class="transition-colors hover:text-[var(--semi-color-primary)]"
            >
              {{ item.name }}
            </NuxtLink>
          </template>
        </NBreadcrumbItem>
      </NBreadcrumb>
    </div>

    <!-- 右侧：操作区 -->
    <HeaderActions />
  </header>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { useRoute } from "vue-router";
import { NBreadcrumb, NBreadcrumbItem } from "naive-ui";
import { HomeIcon } from "@heroicons/vue/24/outline";
import HeaderActions from "./HeaderActions.vue";

const route = useRoute();

const SUBSYSTEM_NAMES: Record<string, { name: string; path: string }> = {
  "/admin":   { name: "平台基础管理", path: "/admin" },
  "/archive": { name: "档案管理系统", path: "/archive" },
};

const breadcrumbs = computed(() => {
  if (route.meta.breadcrumb) {
    return route.meta.breadcrumb as { name: string; path: string }[];
  }
  // 根据当前路径前缀动态确定所属子系统
  const prefix = "/" + route.path.split("/").filter(Boolean)[0];
  const subsystem = SUBSYSTEM_NAMES[prefix] ?? { name: prefix, path: prefix };
  return [subsystem];
});
</script>
