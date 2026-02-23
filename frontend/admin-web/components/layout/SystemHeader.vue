<template>
  <header
    class="h-16 bg-[var(--semi-color-bg-0)] border-b border-base-300 flex items-center justify-between px-6 shadow-sm z-10 w-full"
  >
    <!-- Left: Functional Breadcrumbs -->
    <div class="flex items-center gap-2">
      <Breadcrumb>
        <BreadcrumbItem>
          <NuxtLink
            to="/"
            class="flex items-center gap-1 hover:text-[var(--semi-color-primary)]"
          >
            <HomeIcon class="w-4 h-4" />
            首页
          </NuxtLink>
        </BreadcrumbItem>
        <BreadcrumbItem v-for="(item, index) in breadcrumbs" :key="index">
          <template v-if="index === breadcrumbs.length - 1">
            <span class="font-semibold">{{ item.name }}</span>
          </template>
          <template v-else>
            <NuxtLink
              :to="item.path"
              class="hover:text-[var(--semi-color-primary)]"
              >{{ item.name }}</NuxtLink
            >
          </template>
        </BreadcrumbItem>
      </Breadcrumb>
    </div>

    <!-- Right: Top Actions -->
    <HeaderActions />
  </header>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { useRoute } from "vue-router";
import { Breadcrumb, BreadcrumbItem } from "@kousum/semi-ui-vue";
import { HomeIcon } from "@heroicons/vue/24/outline";
import HeaderActions from "./HeaderActions.vue";

const route = useRoute();

// ─── 面包屑 ───
const breadcrumbs = computed(() => {
  return (
    (route.meta.breadcrumb as { name: string; path: string }[]) || [
      { name: "平台基础管理", path: "/admin" },
    ]
  );
});
</script>
