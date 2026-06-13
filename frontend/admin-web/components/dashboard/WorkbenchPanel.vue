<template>
  <div
    class="flex flex-col overflow-hidden h-full min-h-[500px] rounded-xl border"
    style="background:var(--semi-color-bg-0);border-color:var(--semi-color-border)"
  >
    <NTabs
      v-model:value="activeTabKey"
      type="line"
      size="small"
      class="workbench-tabs flex-1 flex flex-col overflow-hidden"
      :tab-pane-style="{ padding: 0, flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }"
      @update:value="onTabChange"
    >
      <NTabPane
        v-for="tab in tabs"
        :key="tab.key"
        :name="tab.key"
        class="flex-1 overflow-hidden"
      >
        <template #tab>
          <span class="inline-flex items-center gap-1.5">
            {{ tab.label }}
            <span
              class="inline-flex items-center justify-center min-w-[18px] h-[18px] px-1 rounded-full text-[11px] font-semibold"
              :style="tab.danger
                ? 'background:var(--semi-color-danger-light-default);color:var(--semi-color-danger)'
                : 'background:var(--semi-color-primary-light-default);color:var(--semi-color-primary)'"
            >
              {{ tab.count }}
            </span>
          </span>
        </template>

        <!-- 任务列表 -->
        <div class="flex-1 overflow-y-auto" style="max-height:420px">
          <div v-if="loading" class="py-12 flex justify-center">
            <NSpin size="small" />
          </div>
          <div
            v-else-if="!tab.items.length"
            class="py-12 flex flex-col items-center gap-2"
            style="color:var(--semi-color-text-3)"
          >
            <Icon name="heroicons:check-circle" class="w-8 h-8" />
            <span class="text-[13px]">暂无待办，干得漂亮</span>
          </div>
          <ul v-else>
            <li
              v-for="(task, idx) in tab.items"
              :key="task.id"
              class="group cursor-pointer transition-colors duration-150"
              style="padding:14px 20px;border-bottom:1px solid var(--semi-color-border)"
              :style="hoveredIdx === idx ? { background: 'var(--semi-color-fill-0)' } : {}"
              @mouseover="hoveredIdx = idx"
              @mouseleave="hoveredIdx = -1"
              @click="goTo(task)"
            >
              <div class="flex items-center justify-between gap-3">
                <div class="flex items-start gap-3 min-w-0">
                  <div class="mt-1.5 shrink-0">
                    <div class="w-2 h-2 rounded-full" style="background: var(--semi-color-primary)" />
                  </div>
                  <div class="min-w-0">
                    <p
                      class="text-[13px] font-medium truncate transition-colors"
                      :style="{ color: hoveredIdx === idx ? 'var(--semi-color-primary)' : 'var(--semi-color-text-0)' }"
                    >
                      {{ task.title }}
                    </p>
                    <div class="mt-1 flex items-center flex-wrap gap-x-3 gap-y-0.5">
                      <span v-if="task.author" class="text-[11px] flex items-center gap-1" style="color:var(--semi-color-text-2)">
                        <Icon name="heroicons:user" class="w-3 h-3" />{{ task.author }}
                      </span>
                      <span v-if="task.time" class="text-[11px] flex items-center gap-1" style="color:var(--semi-color-text-2)">
                        <Icon name="heroicons:clock" class="w-3 h-3" />{{ timeAgo(task.time) }}
                      </span>
                      <NTag
                        v-if="task.tag"
                        size="small"
                        round
                        :type="TAG_TYPE_MAP[task.tag_color ?? ''] ?? 'default'"
                        style="height:18px;font-size:10px"
                      >
                        {{ task.tag }}
                      </NTag>
                    </div>
                  </div>
                </div>
                <NButton
                  size="small"
                  class="shrink-0 transition-opacity"
                  :style="hoveredIdx === idx ? { opacity: 1 } : { opacity: 0 }"
                >
                  去处理
                </NButton>
              </div>
            </li>
          </ul>
        </div>
      </NTabPane>
    </NTabs>

    <!-- 底部链接 -->
    <div
      class="shrink-0 text-center py-3"
      style="border-top:1px solid var(--semi-color-border);background:var(--semi-color-fill-0)"
    >
      <button
        class="text-[13px] font-medium bg-transparent border-none cursor-pointer"
        style="color:var(--semi-color-primary)"
        @click="load"
      >
        刷新待办 ↻
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { NButton, NSpin, NTabPane, NTabs, NTag } from "naive-ui";
import type { TagProps } from "naive-ui";
import { WorkbenchAPI } from "@/api/appraisal";
import type { WorkbenchTab, WorkbenchTodoItem } from "@/api/appraisal";

const TAG_TYPE_MAP: Record<string, TagProps["type"]> = {
  red: "error",
  orange: "warning",
  amber: "warning",
  yellow: "warning",
  cyan: "info",
  blue: "info",
  violet: "info",
};

const router = useRouter();
const activeTabKey = ref("approval");
const hoveredIdx = ref(-1);
const loading = ref(false);
const tabs = ref<WorkbenchTab[]>([
  { key: "approval", label: "待我审批", count: 0, danger: false, items: [] },
  { key: "appraisal", label: "待鉴定档案", count: 0, danger: false, items: [] },
  { key: "request", label: "查档申请", count: 0, danger: false, items: [] },
  { key: "alert", label: "异常告警", count: 0, danger: true, items: [] },
]);

async function load() {
  loading.value = true;
  try {
    const res = await WorkbenchAPI.overview();
    if (res.code === 0) tabs.value = res.data.tabs;
  } finally {
    loading.value = false;
  }
}

function goTo(task: WorkbenchTodoItem) {
  if (task.link) router.push(task.link);
}

function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const minutes = Math.floor(diff / 60000);
  if (minutes < 1) return "刚刚";
  if (minutes < 60) return `${minutes}分钟前`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}小时前`;
  const days = Math.floor(hours / 24);
  if (days < 30) return `${days}天前`;
  return iso.slice(0, 10);
}

function onTabChange() {
  hoveredIdx.value = -1;
}

onMounted(load);
</script>

<style scoped>
.workbench-tabs :deep(.n-tabs-nav) {
  padding: 0 20px;
  border-bottom: 1px solid var(--semi-color-border);
}
.workbench-tabs :deep(.n-tab-pane) {
  padding: 0;
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}
</style>
