<template>
  <div
    class="rounded-2xl border shadow-sm"
    style="background:var(--semi-color-bg-0);border-color:var(--semi-color-border)"
  >
    <div class="px-6 py-4 border-b" style="border-color:var(--semi-color-border)">
      <h2 class="font-semibold" style="color:var(--semi-color-text-0)">待办任务</h2>
      <p class="text-xs mt-0.5" style="color:var(--semi-color-text-2)">待处理的系统通知与任务</p>
    </div>
    <div class="p-6">
      <div v-if="loading" class="flex justify-center py-16">
        <NSpin size="large" />
      </div>
      <NEmpty v-else-if="!items.length" description="暂无待办任务" class="py-16" />
      <div v-else class="flex flex-col gap-3">
        <div
          v-for="item in items"
          :key="item.id"
          class="flex items-start gap-3 p-4 rounded-xl border transition-colors"
          style="border-color:var(--semi-color-border);background:var(--semi-color-bg-1)"
        >
          <div
            class="w-8 h-8 rounded-lg flex items-center justify-center shrink-0 mt-0.5"
            style="background:oklch(var(--p)/0.1)"
          >
            <Icon name="material-symbols:task-outline" class="text-base" style="color:oklch(var(--p))" />
          </div>
          <div class="flex-1 min-w-0">
            <p class="text-sm font-medium" style="color:var(--semi-color-text-0)">{{ item.title }}</p>
            <p class="text-xs mt-1" style="color:var(--semi-color-text-2)">{{ item.content }}</p>
          </div>
          <NTag
            :type="item.level === 'error' ? 'error' : item.level === 'warning' ? 'warning' : 'info'"
            size="small"
          >
            {{ item.level === "error" ? "紧急" : item.level === "warning" ? "注意" : "普通" }}
          </NTag>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue";
import { NSpin, NEmpty, NTag, useMessage } from "naive-ui";
import { getNotifications, type NotificationItem } from "@/api/notification";

const message = useMessage();
const items = ref<NotificationItem[]>([]);
const loading = ref(false);

onMounted(async () => {
  loading.value = true;
  try {
    const res = await getNotifications({ type: "todo" });
    items.value = res.items || [];
  } catch {
    message.error("加载待办失败");
  } finally {
    loading.value = false;
  }
});
</script>
