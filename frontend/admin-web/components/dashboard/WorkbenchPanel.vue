<template>
  <Card
    :shadows="'always'"
    :header-line="false"
    :body-style="{ padding: 0, display: 'flex', flexDirection: 'column', flex: 1, overflow: 'hidden' }"
    class="flex flex-col overflow-hidden h-full min-h-[500px]"
  >
    <!-- Semi UI Tabs 作为标签栏 -->
    <Tabs
      :active-key="activeTabKey"
      type="line"
      size="small"
      class="workbench-tabs flex-1 flex flex-col overflow-hidden"
      :tab-pane-motion="false"
      @change="onTabChange"
    >
      <TabPane
        v-for="tab in tabs"
        :key="tab.key"
        :item-key="tab.key"
        :tab="renderTabLabel(tab)"
        class="flex-1 overflow-hidden"
      >
        <!-- 任务列表 -->
        <div class="flex-1 overflow-y-auto" style="max-height: 420px;">
          <ul>
            <li
              v-for="(task, idx) in tasksForTab(tab.key)"
              :key="idx"
              class="group cursor-pointer transition-colors duration-150"
              style="padding: 14px 20px; border-bottom: 1px solid var(--semi-color-border);"
              @mouseover="hoveredIdx = idx"
              @mouseleave="hoveredIdx = -1"
              :style="hoveredIdx === idx ? { background: 'var(--semi-color-fill-0)' } : {}"
            >
              <div class="flex items-center justify-between gap-3">
                <div class="flex items-start gap-3 min-w-0">
                  <!-- 未读指示点 -->
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
                      <span class="text-[11px] flex items-center gap-1" style="color: var(--semi-color-text-2);">
                        <Icon name="heroicons:user" class="w-3 h-3" />
                        {{ task.author }}
                      </span>
                      <span class="text-[11px] flex items-center gap-1" style="color: var(--semi-color-text-2);">
                        <Icon name="heroicons:clock" class="w-3 h-3" />
                        {{ task.time }}
                      </span>
                      <Tag
                        v-if="task.tag"
                        size="small"
                        :color="task.tagColor"
                        shape="circle"
                        style="height: 18px; font-size: 10px;"
                      >
                        {{ task.tag }}
                      </Tag>
                    </div>
                  </div>
                </div>
                <!-- 操作按钮 -->
                <Button
                  size="small"
                  type="primary"
                  theme="light"
                  class="shrink-0 transition-opacity"
                  :style="hoveredIdx === idx ? { opacity: 1 } : { opacity: 0 }"
                >
                  审核
                </Button>
              </div>
            </li>
          </ul>
        </div>
      </TabPane>
    </Tabs>

    <!-- 底部链接 -->
    <div
      class="shrink-0 text-center py-3"
      style="border-top: 1px solid var(--semi-color-border); background: var(--semi-color-fill-0);"
    >
      <NuxtLink
        to="/tasks"
        class="text-[13px] font-medium"
        style="color: var(--semi-color-primary); text-decoration: none;"
      >
        查看全部任务 →
      </NuxtLink>
    </div>
  </Card>
</template>

<script setup lang="ts">
import { ref, h } from "vue";
import { Card, Tabs, TabPane, Button, Tag } from "@kousum/semi-ui-vue";

interface Tab {
  key: string;
  label: string;
  count: number;
  danger?: boolean;
}

interface Task {
  title: string;
  author: string;
  time: string;
  unread: boolean;
  tag?: string;
  tagColor?: "red" | "orange" | "amber" | "yellow" | "cyan" | "blue" | "violet";
}

const activeTabKey = ref("approval");
const hoveredIdx = ref(-1);

const tabs: Tab[] = [
  { key: "approval",  label: "待我审批",  count: 12 },
  { key: "appraisal", label: "待鉴定档案", count: 5 },
  { key: "request",   label: "查档申请",  count: 3 },
  { key: "alert",     label: "异常告警",  count: 2, danger: true },
];

const allTasks: Task[] = [
  {
    title: "档案销毁申请 - 项目X文档 (2018-2020)",
    author: "张伟",
    time: "2小时前",
    unread: true,
    tag: "紧急",
    tagColor: "orange",
  },
  {
    title: "元数据更正审批 - 财务部批次 #4021",
    author: "李娜",
    time: "5小时前",
    unread: true,
  },
  {
    title: "数字化入库校验 - 人事档案 Q3季度",
    author: "系统自动",
    time: "昨天",
    unread: false,
  },
  {
    title: '访问控制策略更新请求 - "绝密" 标签',
    author: "管理员组",
    time: "2天前",
    unread: false,
  },
  {
    title: "新用户注册审批：市场部负责人",
    author: "HR系统",
    time: "3天前",
    unread: false,
  },
];

function tasksForTab(key: string): Task[] {
  // 按标签页截取不同长度，模拟不同内容
  const offsets: Record<string, number> = {
    approval: 0,
    appraisal: 1,
    request: 2,
    alert: 3,
  };
  const start = offsets[key] ?? 0;
  return [...allTasks.slice(start), ...allTasks.slice(0, start)];
}

function onTabChange(key: string | number) {
  activeTabKey.value = String(key);
  hoveredIdx.value = -1;
}

// 使用 h() 渲染带数量徽标的 Tab 标题
function renderTabLabel(tab: Tab) {
  return h("span", { style: "display: inline-flex; align-items: center; gap: 5px;" }, [
    h("span", {}, tab.label),
    h(
      "span",
      {
        style: `
          display: inline-flex;
          align-items: center;
          justify-content: center;
          min-width: 18px;
          height: 18px;
          padding: 0 5px;
          border-radius: 9px;
          font-size: 11px;
          font-weight: 600;
          background: ${tab.danger
            ? "var(--semi-color-danger-light-default)"
            : "var(--semi-color-primary-light-default)"};
          color: ${tab.danger
            ? "var(--semi-color-danger)"
            : "var(--semi-color-primary)"};
        `,
      },
      String(tab.count),
    ),
  ]);
}
</script>

<style scoped>
/* 让 Tabs 的 tabBar 撑满宽度并设置左右内边距 */
.workbench-tabs :deep(.semi-tabs-bar) {
  padding: 0 20px;
  border-bottom: 1px solid var(--semi-color-border);
}

/* TabPane 内容区去掉多余 padding */
.workbench-tabs :deep(.semi-tabs-content) {
  padding: 0;
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.workbench-tabs :deep(.semi-tabs-pane) {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}
</style>
