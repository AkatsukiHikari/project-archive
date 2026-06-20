<template>
  <div class="h-screen flex flex-col overflow-hidden" style="background: var(--semi-color-fill-0)">
    <LayoutAppHeader :show-search="false" />
    <main class="flex-1 min-h-0 overflow-hidden">
      <slot />
    </main>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from "vue";
import { useUserStore } from "@/stores/user";

// 新标签页 Pinia 是空的：有 token 但未拉用户信息时补拉，避免顶栏头像显示英文占位
const userStore = useUserStore();
onMounted(() => {
  if (userStore.token && !userStore.userInfo) {
    userStore.getUserInfo().catch(() => undefined);
  }
});
</script>
