<template>
  <div
    class="rounded-2xl bg-[var(--semi-color-bg-0)] border border-[var(--semi-color-border)] shadow-sm"
  >
    <div class="px-6 py-4 border-b border-[var(--semi-color-border)]">
      <h2 class="font-semibold text-[var(--semi-color-text-0)]">待办任务</h2>
      <p class="text-xs text-[var(--semi-color-text-2)] mt-0.5">
        待处理的系统通知与任务
      </p>
    </div>
    <div class="p-6">
      <div v-if="loading" class="flex justify-center py-16">
        <Spin size="large" />
      </div>
      <Empty
        v-else-if="!items.length"
        description="暂无待办任务"
        class="py-16"
      />
      <div v-else class="flex flex-col gap-3">
        <div
          v-for="item in items"
          :key="item.id"
          class="flex items-start gap-3 p-4 rounded-xl border border-[var(--semi-color-border)] bg-[var(--semi-color-bg-1)] hover:bg-[var(--semi-color-fill-0)] transition-colors"
        >
          <div
            class="w-8 h-8 rounded-lg bg-[oklch(var(--p)/0.1)] flex items-center justify-center shrink-0 mt-0.5"
          >
            <Icon
              name="material-symbols:task-outline"
              class="text-[oklch(var(--p))] text-base"
            />
          </div>
          <div class="flex-1 min-w-0">
            <p class="text-sm font-medium text-[var(--semi-color-text-0)]">
              {{ item.title }}
            </p>
            <p class="text-xs text-[var(--semi-color-text-2)] mt-1">
              {{ item.content }}
            </p>
          </div>
          <Tag
            :color="
              item.level === 'error'
                ? 'red'
                : item.level === 'warning'
                  ? 'orange'
                  : 'blue'
            "
            size="small"
          >
            {{
              item.level === "error"
                ? "紧急"
                : item.level === "warning"
                  ? "注意"
                  : "普通"
            }}
          </Tag>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue";
import { Spin, Empty, Tag, Toast } from "@kousum/semi-ui-vue";
import { getNotifications, type NotificationItem } from "@/api/notification";

const items = ref<NotificationItem[]>([]);
const loading = ref(false);

onMounted(async () => {
  loading.value = true;
  try {
    const res = await getNotifications({ type: "todo" });
    items.value = res.items || [];
  } catch {
    Toast.error("加载待办失败");
  } finally {
    loading.value = false;
  }
});
</script>
