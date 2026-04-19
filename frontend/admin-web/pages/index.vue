<template>
  <div class="flex flex-col gap-6">

    <!-- AI 智能助手 Hero -->
    <div class="bg-base-100 rounded-2xl px-8 py-7 ai-hero-card">
      <!-- 顶部：问候 + 进入完整对话 -->
      <div class="flex items-start justify-between gap-4 mb-6">
        <div>
          <div class="flex items-center gap-2 mb-1.5">
            <div class="w-6 h-6 rounded-md bg-primary/10 flex items-center justify-center">
              <Icon name="heroicons:sparkles" class="w-4 h-4 text-primary" />
            </div>
            <span class="text-base-content/50 text-xs font-medium uppercase tracking-widest">
              AI 档案智能助手 · 基于 RAG 语义检索
            </span>
          </div>
          <h1 class="text-base-content text-2xl font-bold">{{ greeting }}，{{ displayName }}</h1>
          <p class="text-base-content/50 text-sm mt-1">{{ today }}</p>
        </div>
        <NButton class="shrink-0" @click="router.push('/ai')">
          进入完整对话
          <template #icon>
            <Icon name="heroicons:arrow-top-right-on-square" class="w-4 h-4" />
          </template>
        </NButton>
      </div>

      <!-- AI 输入框 -->
      <div class="relative">
        <div class="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
          <Icon name="heroicons:magnifying-glass" class="w-5 h-5 text-base-content/30" />
        </div>
        <input
          v-model="aiQuery"
          type="text"
          placeholder="向档案库提问，例如：查找 2023 年度财务档案、人事档案保存期限规定..."
          class="ai-search-input w-full h-12 pl-11 pr-14 text-sm rounded-xl outline-none"
          @keydown.enter="submitAiQuery"
        >
        <button
          class="absolute inset-y-0 right-0 pr-4 flex items-center text-base-content/30 hover:text-primary transition-colors cursor-pointer"
          :disabled="!aiQuery.trim()"
          @click="submitAiQuery"
        >
          <Icon name="heroicons:paper-airplane" class="w-5 h-5" />
        </button>
      </div>

      <!-- 快捷问题 -->
      <div class="mt-4 flex flex-wrap gap-2">
        <button
          v-for="q in quickQuestions"
          :key="q"
          class="ai-quick-btn text-xs px-3 py-1.5 rounded-full transition-all cursor-pointer"
          @click="askQuestion(q)"
        >
          {{ q }}
        </button>
      </div>
    </div>

    <!-- 系统公告 -->
    <DashboardAnnouncementBanner />

    <!-- 业务子系统 -->
    <section>
      <CommonSectionTitle title="业务子系统" icon="heroicons:squares-2x2" class="mb-4" />
      <DashboardAppCardGrid :apps="bizApps" />
    </section>

    <!-- 工作台主区域 -->
    <div class="grid grid-cols-1 lg:grid-cols-12 gap-6">
      <section class="lg:col-span-8 flex flex-col gap-4">
        <CommonSectionTitle title="系统工作台" icon="heroicons:inbox-stack" />
        <DashboardWorkbenchPanel class="flex-1" />
      </section>
      <section class="lg:col-span-4 flex flex-col gap-4">
        <CommonSectionTitle title="工具与日程" icon="heroicons:view-columns" />
        <DashboardPersonalPanel class="flex-1" />
      </section>
    </div>

  </div>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";
import { useRouter } from "vue-router";
import { NButton } from "naive-ui";
import { useUserStore } from "@/stores/user";

definePageMeta({ layout: "portal", middleware: "auth" });

const router = useRouter();
const userStore = useUserStore();

const displayName = computed(
  () => userStore.userInfo?.full_name || userStore.userInfo?.username || "用户",
);

const greeting = computed(() => {
  const h = new Date().getHours();
  if (h < 6) return "夜深了";
  if (h < 12) return "早上好";
  if (h < 14) return "中午好";
  if (h < 18) return "下午好";
  return "晚上好";
});

const today = computed(() =>
  new Date().toLocaleDateString("zh-CN", {
    year: "numeric", month: "long", day: "numeric", weekday: "long",
  }),
);

const aiQuery = ref("");

const quickQuestions = [
  "查找2023年度财务档案",
  "人事档案保存期限规定",
  "涉密档案处理流程",
  "如何申请档案利用？",
];

function submitAiQuery() {
  const q = aiQuery.value.trim();
  if (!q) return;
  router.push(`/ai?q=${encodeURIComponent(q)}`);
}

function askQuestion(q: string) {
  router.push(`/ai?q=${encodeURIComponent(q)}`);
}

const bizApps = [
  {
    name: "档案管理",
    description: "全生命周期管理：收集、整理、归档与存储。",
    icon: "heroicons:archive-box",
    iconBg: "bg-primary/10",
    iconColor: "text-primary",
    hoverColor: "group-hover:text-primary",
    href: "/archive",
  },
  {
    name: "数据资源中心",
    description: "全域档案资源汇聚，多源异构数据集成与融合。",
    icon: "heroicons:circle-stack",
    iconBg: "bg-sky-500/10",
    iconColor: "text-sky-500",
    hoverColor: "group-hover:text-sky-500",
    href: "/data-center",
  },
  {
    name: "利用服务中心",
    description: "面向公众的查档服务，检索门户与借阅管理。",
    icon: "heroicons:user-group",
    iconBg: "bg-warning/10",
    iconColor: "text-warning",
    hoverColor: "group-hover:text-warning",
    href: "/service",
  },
  {
    name: "平台基础管理",
    description: "IAM 身份认证、RBAC 权限配置及系统参数。",
    icon: "heroicons:cog-8-tooth",
    iconBg: "bg-base-300",
    iconColor: "text-base-content/70",
    hoverColor: "group-hover:text-base-content",
    href: "/admin",
  },
  {
    name: "系统审计中心",
    description: "操作日志、安全监控告警与统计报表。",
    icon: "heroicons:clipboard-document-check",
    iconBg: "bg-error/10",
    iconColor: "text-error",
    hoverColor: "group-hover:text-error",
    href: "/audit",
  },
];
</script>

<style scoped>
.ai-hero-card {
  box-shadow: 0 1px 3px oklch(var(--bc) / 0.06), 0 4px 12px oklch(var(--bc) / 0.08);
}
.ai-search-input {
  background: oklch(var(--b2));
  border: none;
  color: oklch(var(--bc));
  transition: box-shadow 0.2s;
}
.ai-search-input::placeholder { color: oklch(var(--bc) / 0.35); }
.ai-search-input:focus { box-shadow: 0 0 0 2px oklch(var(--p) / 0.3); }
.ai-quick-btn {
  background: oklch(var(--b2));
  border: none;
  color: oklch(var(--bc) / 0.6);
  transition: background 0.15s, color 0.15s;
}
.ai-quick-btn:hover { background: oklch(var(--p) / 0.1); color: oklch(var(--p)); }
</style>
