<template>
  <div class="flex flex-col gap-6">

    <!-- ══════════════════════════════════════════════════════════
         AI 智能助手 Hero —— 系统核心亮点，置顶全宽展示
    ══════════════════════════════════════════════════════════ -->
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
          <h1 class="text-base-content text-2xl font-bold">
            {{ greeting }}，{{ displayName }}
          </h1>
          <p class="text-base-content/50 text-sm mt-1">{{ today }}</p>
        </div>
        <Button
          theme="outline"
          type="primary"
          size="default"
          class="shrink-0"
          @click="router.push('/ai')"
        >
          进入完整对话
          <template #icon>
            <Icon name="heroicons:arrow-top-right-on-square" class="w-4 h-4" />
          </template>
        </Button>
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

    <!-- ══════════════════════════════════════════════════════════
         数据概览 —— 四个核心指标
    ══════════════════════════════════════════════════════════ -->
    <div class="grid grid-cols-2 lg:grid-cols-4 gap-4">
      <Card
        v-for="stat in stats"
        :key="stat.label"
        :shadows="'hover'"
        :header-line="false"
        :body-style="{ padding: '20px' }"
        class="cursor-default"
      >
        <div class="flex items-start justify-between">
          <div>
            <div class="text-[12px] mb-1" style="color: var(--semi-color-text-2);">
              {{ stat.label }}
            </div>
            <div class="text-[26px] font-bold leading-none" style="color: var(--semi-color-text-0);">
              {{ stat.value }}
            </div>
            <div class="text-[11px] mt-1.5 flex items-center gap-1" :class="stat.trendUp ? 'text-success' : 'text-base-content/40'">
              <Icon :name="stat.trendUp ? 'heroicons:arrow-trending-up' : 'heroicons:minus'" class="w-3 h-3" />
              {{ stat.trend }}
            </div>
          </div>
          <div
            class="w-10 h-10 rounded-xl flex items-center justify-center shrink-0"
            :class="stat.iconBg"
          >
            <Icon :name="stat.icon" class="w-5 h-5" :class="stat.iconColor" />
          </div>
        </div>
      </Card>
    </div>

    <!-- ══════════════════════════════════════════════════════════
         AI 功能入口 —— 单独成区，视觉权重高于普通业务模块
    ══════════════════════════════════════════════════════════ -->
    <section>
      <div class="flex items-center justify-between mb-4">
        <CommonSectionTitle title="AI 智能功能" icon="heroicons:cpu-chip" />
        <span class="text-[11px] font-semibold uppercase tracking-widest px-2 py-0.5 rounded-full bg-primary/10 text-primary">
          Powered by RAG · Ollama
        </span>
      </div>
      <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
        <NuxtLink
          v-for="app in aiApps"
          :key="app.name"
          :to="app.href"
          class="block ai-module-card rounded-xl p-5 transition-all duration-200 cursor-pointer group"
          style="text-decoration: none;"
        >
          <div class="flex items-start gap-4">
            <div
              class="w-12 h-12 rounded-xl flex items-center justify-center shrink-0 transition-transform duration-200 group-hover:scale-105"
              :class="app.iconBg"
            >
              <Icon :name="app.icon" class="w-6 h-6" :class="app.iconColor" />
            </div>
            <div class="min-w-0">
              <div class="flex items-center gap-2 mb-1">
                <span class="text-[14px] font-semibold" style="color: var(--semi-color-text-0);">
                  {{ app.name }}
                </span>
                <Tag v-if="app.badge" size="small" color="blue" shape="circle">
                  {{ app.badge }}
                </Tag>
              </div>
              <p class="text-[12px] leading-relaxed" style="color: var(--semi-color-text-2);">
                {{ app.description }}
              </p>
            </div>
          </div>
        </NuxtLink>
      </div>
    </section>

    <!-- ══════════════════════════════════════════════════════════
         业务应用 —— 常规功能模块入口
    ══════════════════════════════════════════════════════════ -->
    <section>
      <CommonSectionTitle title="业务与管理" icon="heroicons:squares-2x2" class="mb-4" />
      <DashboardAppCardGrid :apps="bizApps" />
    </section>

    <!-- ══════════════════════════════════════════════════════════
         工作台 + 我的日程
    ══════════════════════════════════════════════════════════ -->
    <div class="grid grid-cols-1 lg:grid-cols-12 gap-6">
      <section class="lg:col-span-8 flex flex-col">
        <CommonSectionTitle title="系统工作台" icon="heroicons:inbox-stack" class="mb-4" />
        <DashboardWorkbenchPanel class="flex-1" />
      </section>
      <section class="lg:col-span-4 flex flex-col">
        <CommonSectionTitle title="我的日程" icon="heroicons:calendar-days" class="mb-4" />
        <DashboardSchedulePanel class="flex-1 min-h-[500px]" />
      </section>
    </div>

  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { Card, Button, Tag } from "@kousum/semi-ui-vue";
import { useUserStore } from "@/stores/user";
import { ScheduleAPI } from "@/api/schedule";

definePageMeta({
  layout: "portal",
  middleware: "auth",
});

const router = useRouter();
const userStore = useUserStore();

// ── 问候语 ────────────────────────────────────────────────────
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
    year: "numeric",
    month: "long",
    day: "numeric",
    weekday: "long",
  }),
);

// ── AI 输入 ──────────────────────────────────────────────────
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

// ── 数据概览（当前为模拟数据，可接入真实 API）────────────────
const stats = [
  {
    label: "档案总量",
    value: "12,847",
    trend: "较上月 +3.2%",
    trendUp: true,
    icon: "heroicons:archive-box",
    iconBg: "bg-primary/10",
    iconColor: "text-primary",
  },
  {
    label: "本月入库",
    value: "156",
    trend: "较上月 +12",
    trendUp: true,
    icon: "heroicons:inbox-arrow-down",
    iconBg: "bg-success/10",
    iconColor: "text-success",
  },
  {
    label: "待处理任务",
    value: "23",
    trend: "需要关注",
    trendUp: false,
    icon: "heroicons:clock",
    iconBg: "bg-warning/10",
    iconColor: "text-warning",
  },
  {
    label: "AI 对话次数",
    value: "89",
    trend: "今日 +14",
    trendUp: true,
    icon: "heroicons:cpu-chip",
    iconBg: "bg-secondary/10",
    iconColor: "text-secondary",
  },
];

// ── AI 功能模块 ──────────────────────────────────────────────
const aiApps = [
  {
    name: "AI 档案对话助手",
    description: "自然语言提问，RAG 语义检索全库档案，支持多轮对话与知识追溯。",
    icon: "heroicons:chat-bubble-left-ellipsis",
    iconBg: "bg-primary/10",
    iconColor: "text-primary",
    badge: "NEW",
    href: "/ai",
  },
  {
    name: "智能四性检测",
    description: "AI 驱动的真实性、完整性、可用性、安全性自动检测，生成合规报告。",
    icon: "heroicons:shield-check",
    iconBg: "bg-success/10",
    iconColor: "text-success",
    badge: null,
    href: "/preservation",
  },
  {
    name: "知识库管理",
    description: "管理 RAG 知识库，上传文档、同步档案，配置 Ollama 模型与检索策略。",
    icon: "heroicons:book-open",
    iconBg: "bg-violet-500/10",
    iconColor: "text-violet-500",
    badge: null,
    href: "/ai/knowledge",
  },
];

// ── 业务模块 ─────────────────────────────────────────────────
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
  {
    name: "日程与任务",
    description: "工作日程管理、重要事项提醒与任务跟踪。",
    icon: "heroicons:calendar-days",
    iconBg: "bg-teal-500/10",
    iconColor: "text-teal-500",
    hoverColor: "group-hover:text-teal-500",
    href: "/schedule",
  },
];

// ── 日程通知（保留，用于工作台参考）─────────────────────────
onMounted(async () => {
  try {
    const res = await ScheduleAPI.list(new Date().toISOString());
    if (!res.data?.length) return;
    const now = new Date();
    const next = res.data.find((e) => new Date(e.start_time).getTime() > now.getTime());
    if (next) {
      // 可在此触发 Semi UI Notification 通知
    }
  } catch {
    // 静默失败
  }
});
</script>

<style scoped>
/* Hero 卡片：阴影浮起，不用 border */
.ai-hero-card {
  box-shadow:
    0 1px 3px oklch(var(--bc) / 0.06),
    0 4px 12px oklch(var(--bc) / 0.08);
}

/* 搜索输入框：bg-base-200 往里凹，形成层次感 */
.ai-search-input {
  background: oklch(var(--b2));
  border: none;
  color: oklch(var(--bc));
  transition: box-shadow 0.2s;
}
.ai-search-input::placeholder {
  color: oklch(var(--bc) / 0.35);
}
.ai-search-input:focus {
  box-shadow: 0 0 0 2px oklch(var(--p) / 0.3);
}

/* 快捷问题按钮：同 base-200 背景，hover 变 primary tint */
.ai-quick-btn {
  background: oklch(var(--b2));
  border: none;
  color: oklch(var(--bc) / 0.6);
  transition: background 0.15s, color 0.15s;
}
.ai-quick-btn:hover {
  background: oklch(var(--p) / 0.1);
  color: oklch(var(--p));
}

/* AI 功能模块卡片 */
.ai-module-card {
  background: var(--semi-color-bg-1);
  border: 1px solid var(--semi-color-border);
}
.ai-module-card:hover {
  border-color: var(--semi-color-primary-light-hover);
  box-shadow: 0 4px 16px rgba(25, 120, 229, 0.12);
  transform: translateY(-1px);
}
</style>
