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
          <ul>
            <li
              v-for="(task, idx) in tasksForTab(tab.key)"
              :key="idx"
              class="group cursor-pointer transition-colors duration-150"
              style="padding:14px 20px;border-bottom:1px solid var(--semi-color-border)"
              @mouseover="hoveredIdx = idx"
              @mouseleave="hoveredIdx = -1"
              :style="hoveredIdx === idx ? { background: 'var(--semi-color-fill-0)' } : {}"
            >
              <div class="flex items-center justify-between gap-3">
                <div class="flex items-start gap-3 min-w-0">
                  <div class="mt-1.5 shrink-0">
                    <div
                      class="w-2 h-2 rounded-full"
                      :style="task.unread
                        ? { background: 'var(--semi-color-primary)' }
                        : { background: 'var(--semi-color-fill-2)' }"
                    />
                  </div>
                  <div class="min-w-0">
                    <p
                      class="text-[13px] font-medium truncate transition-colors"
                      :style="{ color: hoveredIdx === idx ? 'var(--semi-color-primary)' : 'var(--semi-color-text-0)' }"
                    >
                      {{ task.title }}
                    </p>
                    <div class="mt-1 flex items-center flex-wrap gap-x-3 gap-y-0.5">
                      <span class="text-[11px] flex items-center gap-1" style="color:var(--semi-color-text-2)">
                        <Icon name="heroicons:user" class="w-3 h-3" />{{ task.author }}
                      </span>
                      <span class="text-[11px] flex items-center gap-1" style="color:var(--semi-color-text-2)">
                        <Icon name="heroicons:clock" class="w-3 h-3" />{{ task.time }}
                      </span>
                      <NTag
                        v-if="task.tag"
                        size="small"
                        round
                        :type="TAG_TYPE_MAP[task.tagColor ?? ''] ?? 'default'"
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
                  审核
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
      <NuxtLink to="/tasks" class="text-[13px] font-medium" style="color:var(--semi-color-primary);text-decoration:none">
        查看全部任务 →
      </NuxtLink>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from "vue";
import { NTabs, NTabPane, NButton, NTag } from "naive-ui";
import type { TagProps } from "naive-ui";

interface Tab { key: string; label: string; count: number; danger?: boolean }
interface Task {
  title: string;
  author: string;
  time: string;
  unread: boolean;
  tag?: string;
  tagColor?: string;
}

const TAG_TYPE_MAP: Record<string, TagProps["type"]> = {
  red: "error",
  orange: "warning",
  amber: "warning",
  yellow: "warning",
  cyan: "info",
  blue: "info",
  violet: "info",
};

const activeTabKey = ref("approval");
const hoveredIdx = ref(-1);

const tabs: Tab[] = [
  { key: "approval",  label: "待我审批",  count: 12 },
  { key: "appraisal", label: "待鉴定档案", count: 5 },
  { key: "request",   label: "查档申请",  count: 3 },
  { key: "alert",     label: "异常告警",  count: 2, danger: true },
];

const allTasks: Task[] = [
  { title: "档案销毁申请 - 项目X文档 (2018-2020)", author: "张伟", time: "2小时前", unread: true, tag: "紧急", tagColor: "orange" },
  { title: "元数据更正审批 - 财务部批次 #4021", author: "李娜", time: "5小时前", unread: true },
  { title: "数字化入库校验 - 人事档案 Q3季度", author: "系统自动", time: "昨天", unread: false },
  { title: '访问控制策略更新请求 - "绝密" 标签', author: "管理员组", time: "2天前", unread: false },
  { title: "新用户注册审批：市场部负责人", author: "HR系统", time: "3天前", unread: false },
];

function tasksForTab(key: string): Task[] {
  const offsets: Record<string, number> = { approval: 0, appraisal: 1, request: 2, alert: 3 };
  const start = offsets[key] ?? 0;
  return [...allTasks.slice(start), ...allTasks.slice(0, start)];
}

function onTabChange() {
  hoveredIdx.value = -1;
}
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
