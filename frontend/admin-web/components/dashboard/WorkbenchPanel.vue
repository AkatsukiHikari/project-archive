<template>
  <div
    class="bg-base-100 rounded-xl shadow-card border border-base-300 flex flex-col overflow-hidden h-full min-h-[500px]"
  >
    <!-- 标签栏 -->
    <div class="border-b border-base-300 px-6 pt-2">
      <nav
        class="-mb-px flex space-x-6 overflow-x-auto"
        aria-label="工作台标签"
      >
        <button
          v-for="(tab, idx) in tabs"
          :key="tab.key"
          class="whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm flex items-center gap-2 transition-colors shrink-0"
          :class="
            activeTab === idx
              ? 'border-primary text-primary'
              : tab.danger
                ? 'border-transparent text-error hover:text-error/80 hover:border-error/30'
                : 'border-transparent text-base-content/60 hover:text-base-content hover:border-base-300'
          "
          @click="activeTab = idx"
        >
          <Icon :name="tab.icon" class="w-4 h-4" />
          {{ tab.label }}
          <span
            class="py-0.5 px-2.5 rounded-full text-xs font-semibold"
            :class="
              activeTab === idx
                ? 'bg-primary/10 text-primary'
                : tab.danger
                  ? 'bg-error/10 text-error'
                  : 'bg-base-200 text-base-content/60'
            "
          >
            {{ tab.count }}
          </span>
        </button>
      </nav>
    </div>

    <!-- 任务列表 -->
    <div class="flex-1 overflow-auto">
      <ul class="divide-y divide-base-200">
        <li
          v-for="(task, idx) in tasks"
          :key="idx"
          class="p-4 hover:bg-base-200/50 transition-colors group cursor-pointer"
        >
          <div class="flex items-center justify-between">
            <div class="flex items-start gap-4">
              <div class="mt-1">
                <div
                  class="h-2 w-2 rounded-full mt-2"
                  :class="task.unread ? 'bg-primary' : 'bg-base-300'"
                />
              </div>
              <div>
                <p
                  class="text-sm font-semibold text-base-content group-hover:text-primary transition-colors"
                >
                  {{ task.title }}
                </p>
                <div
                  class="mt-1 flex items-center gap-3 text-xs text-base-content/60 flex-wrap"
                >
                  <span class="flex items-center gap-1">
                    <Icon name="heroicons:user" class="w-3.5 h-3.5" />
                    发起人: {{ task.author }}
                  </span>
                  <span class="w-1 h-1 rounded-full bg-base-300" />
                  <span class="flex items-center gap-1">
                    <Icon name="heroicons:clock" class="w-3.5 h-3.5" />
                    {{ task.time }}
                  </span>
                  <template v-if="task.tag">
                    <span class="w-1 h-1 rounded-full bg-base-300" />
                    <span
                      class="px-2 py-0.5 rounded text-[10px] font-medium uppercase tracking-wider"
                      :class="task.tagClass"
                    >
                      {{ task.tag }}
                    </span>
                  </template>
                </div>
              </div>
            </div>
            <button
              class="text-sm font-medium text-primary hover:text-primary-focus border border-primary/20 hover:border-primary px-4 py-1.5 rounded-lg transition-all opacity-0 group-hover:opacity-100 shrink-0"
            >
              审核
            </button>
          </div>
        </li>
      </ul>
    </div>

    <!-- 底部链接 -->
    <div class="p-4 border-t border-base-300 bg-base-200/50 text-center">
      <NuxtLink
        to="/tasks"
        class="text-sm font-medium text-primary hover:underline"
      >
        查看全部任务
      </NuxtLink>
    </div>
  </div>
</template>

<script setup lang="ts">
interface Tab {
  key: string;
  label: string;
  icon: string;
  count: number;
  danger?: boolean;
}

interface Task {
  title: string;
  author: string;
  time: string;
  unread: boolean;
  tag?: string;
  tagClass?: string;
}

const activeTab = ref(0);

const tabs: Tab[] = [
  { key: "approval", label: "待我审批", icon: "heroicons:clock", count: 12 },
  {
    key: "appraisal",
    label: "待鉴定档案",
    icon: "heroicons:magnifying-glass-circle",
    count: 5,
  },
  {
    key: "request",
    label: "查档申请",
    icon: "heroicons:folder-open",
    count: 3,
  },
  {
    key: "alert",
    label: "异常告警",
    icon: "heroicons:exclamation-triangle",
    count: 2,
    danger: true,
  },
];

const tasks: Task[] = [
  {
    title: "档案销毁申请 - 项目X文档 (2018-2020)",
    author: "张伟",
    time: "2小时前",
    unread: true,
    tag: "紧急",
    tagClass: "bg-warning/10 text-warning",
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
    title: "新用户注册审批: 市场部负责人",
    author: "HR系统",
    time: "3天前",
    unread: false,
  },
];
</script>
