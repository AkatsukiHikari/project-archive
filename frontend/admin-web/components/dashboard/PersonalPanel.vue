<template>
  <div class="flex flex-col gap-4">

    <!-- ── 档案到期预警 ────────────────────────────────── -->
    <div class="panel-card rounded-xl overflow-hidden">
      <div class="panel-header px-4 py-3 flex items-center justify-between">
        <div class="flex items-center gap-2">
          <Icon name="heroicons:clock" class="w-3.5 h-3.5 text-warning" />
          <span class="text-[11px] font-semibold uppercase tracking-widest" style="color:var(--semi-color-text-2)">
            档案到期预警
          </span>
        </div>
        <NuxtLink
          to="/preservation"
          class="text-[11px] font-medium flex items-center gap-0.5 transition-opacity hover:opacity-70"
          style="color:var(--semi-color-primary);text-decoration:none"
        >
          前往鉴定 <Icon name="heroicons:arrow-top-right-on-square" class="w-3 h-3" />
        </NuxtLink>
      </div>

      <div v-if="alertLoading" class="flex items-center justify-center py-5">
        <NSpin size="small" />
      </div>
      <div v-else>
        <div
          v-for="tier in alertTiers"
          :key="tier.key"
          class="alert-tier-row flex items-center gap-3 px-4 py-3 transition-colors cursor-pointer"
          style="border-top:1px solid var(--semi-color-border)"
          @click="tier.count > 0 && router.push('/preservation')"
        >
          <div class="w-2 h-2 rounded-full shrink-0" :class="tier.dotColor" />
          <span class="text-[12px] flex-1" style="color:var(--semi-color-text-1)">{{ tier.label }}</span>
          <div v-if="tier.count > 0" class="flex items-center gap-1.5">
            <span class="text-[13px] font-bold tabular-nums" :class="tier.countColor">{{ tier.count }}</span>
            <span class="text-[11px]" style="color:var(--semi-color-text-2)">件</span>
            <Icon v-if="tier.key === 'urgent'" name="heroicons:chevron-right" class="w-3 h-3 ml-0.5" style="color:var(--semi-color-text-2)" />
          </div>
          <span v-else class="text-[11px]" style="color:var(--semi-color-text-2)">暂无</span>
        </div>
      </div>
    </div>

    <!-- ── AI 智能工具 ─────────────────────────────────── -->
    <div class="panel-card rounded-xl overflow-hidden">
      <div class="panel-header px-4 py-3 flex items-center gap-2">
        <Icon name="heroicons:cpu-chip" class="w-3.5 h-3.5 text-primary" />
        <span class="text-[11px] font-semibold uppercase tracking-widest" style="color:var(--semi-color-text-2)">
          AI 智能工具
        </span>
        <span class="ml-auto text-[9px] px-1.5 py-0.5 rounded-full bg-primary/10 text-primary font-bold uppercase tracking-wide">
          RAG
        </span>
      </div>
      <div>
        <NuxtLink
          v-for="tool in aiTools"
          :key="tool.name"
          :to="tool.href"
          class="ai-tool-item flex items-center gap-3 px-4 py-3 transition-colors cursor-pointer"
          style="text-decoration:none;border-top:1px solid var(--semi-color-border)"
        >
          <div class="w-8 h-8 rounded-lg flex items-center justify-center shrink-0" :class="tool.iconBg">
            <Icon :name="tool.icon" class="w-4 h-4" :class="tool.iconColor" />
          </div>
          <div class="min-w-0 flex-1">
            <div class="flex items-center gap-1.5">
              <span class="text-[13px] font-medium" style="color:var(--semi-color-text-0)">{{ tool.name }}</span>
              <span v-if="tool.badge" class="text-[9px] font-bold px-1 py-0.5 rounded bg-primary/10 text-primary uppercase">
                {{ tool.badge }}
              </span>
            </div>
            <p class="text-[11px] truncate mt-0.5" style="color:var(--semi-color-text-2)">{{ tool.desc }}</p>
          </div>
          <Icon name="heroicons:chevron-right" class="w-3.5 h-3.5 shrink-0 ai-tool-arrow" style="color:var(--semi-color-text-2)" />
        </NuxtLink>
      </div>
    </div>

    <!-- ── 我的日程 ───────────────────────────────────── -->
    <div class="panel-card rounded-xl overflow-hidden">
      <div class="panel-header px-4 py-3 flex items-center justify-between">
        <div class="flex items-center gap-2">
          <Icon name="heroicons:calendar-days" class="w-3.5 h-3.5 text-primary" />
          <span class="text-[11px] font-semibold uppercase tracking-widest" style="color:var(--semi-color-text-2)">
            我的日程
          </span>
        </div>
        <NuxtLink
          to="/schedule"
          class="text-[11px] font-medium flex items-center gap-0.5 transition-opacity hover:opacity-70"
          style="color:var(--semi-color-primary);text-decoration:none"
        >
          进入日程 <Icon name="heroicons:arrow-top-right-on-square" class="w-3 h-3" />
        </NuxtLink>
      </div>

      <div
        class="px-4 py-2 text-[11px]"
        style="color:var(--semi-color-text-2);border-top:1px solid var(--semi-color-border);border-bottom:1px solid var(--semi-color-border);background:var(--semi-color-fill-0)"
      >
        {{ todayLabel }}
      </div>

      <div>
        <div v-if="scheduleLoading" class="flex items-center justify-center py-6">
          <NSpin size="small" />
        </div>
        <template v-else-if="todayEvents.length > 0">
          <div
            v-for="event in todayEvents"
            :key="event.id"
            class="schedule-item flex items-start gap-2.5 px-4 py-3 transition-colors"
            style="border-bottom:1px solid var(--semi-color-border)"
          >
            <div class="w-0.5 rounded-full shrink-0 mt-0.5 self-stretch" style="background:var(--semi-color-primary);min-height:32px" />
            <div class="min-w-0 flex-1">
              <p class="text-[12px] font-medium truncate" style="color:var(--semi-color-text-0)">{{ event.title }}</p>
              <p class="text-[11px] mt-0.5" style="color:var(--semi-color-text-2)">
                <template v-if="event.is_all_day">全天</template>
                <template v-else>{{ formatTime(event.start_time) }} — {{ formatTime(event.end_time) }}</template>
              </p>
            </div>
          </div>
        </template>
        <div v-else class="flex flex-col items-center gap-2 py-6 px-4 text-center">
          <Icon name="heroicons:calendar" class="w-8 h-8" style="color:var(--semi-color-fill-2)" />
          <p class="text-[12px]" style="color:var(--semi-color-text-2)">今日暂无日程安排</p>
          <NuxtLink
            to="/schedule"
            class="text-[11px] font-medium hover:opacity-70 transition-opacity"
            style="color:var(--semi-color-primary);text-decoration:none"
          >
            + 添加日程事项
          </NuxtLink>
        </div>
      </div>
    </div>

  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { useRouter } from "vue-router";
import { NSpin } from "naive-ui";
import { ScheduleAPI, type ScheduleEvent } from "@/api/schedule";

const router = useRouter();

const alertLoading = ref(false);
const alertTiers = ref([
  { key: "urgent",  label: "7 天内到期",  count: 8,  dotColor: "bg-error",   countColor: "text-error" },
  { key: "soon",    label: "30 天内到期", count: 23, dotColor: "bg-warning",  countColor: "text-warning" },
  { key: "pending", label: "90 天内到期", count: 67, dotColor: "bg-info",     countColor: "text-info" },
]);

const aiTools = [
  {
    name: "AI 档案对话助手",
    desc: "自然语言检索全库档案",
    icon: "heroicons:chat-bubble-left-ellipsis",
    iconBg: "bg-primary/10",
    iconColor: "text-primary",
    badge: "NEW",
    href: "/ai",
  },
  {
    name: "智能四性检测",
    desc: "真实性、完整性、安全性自动检测",
    icon: "heroicons:shield-check",
    iconBg: "bg-success/10",
    iconColor: "text-success",
    badge: null,
    href: "/preservation",
  },
  {
    name: "知识库管理",
    desc: "管理 RAG 知识库与检索策略",
    icon: "heroicons:book-open",
    iconBg: "bg-violet-500/10",
    iconColor: "text-violet-500",
    badge: null,
    href: "/ai/knowledge",
  },
];

const scheduleLoading = ref(false);
const todayEvents = ref<ScheduleEvent[]>([]);

const todayLabel = computed(() =>
  new Date().toLocaleDateString("zh-CN", { month: "long", day: "numeric", weekday: "long" }),
);

function formatTime(iso: string): string {
  return new Date(iso).toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit", hour12: false });
}

onMounted(async () => {
  scheduleLoading.value = true;
  try {
    const start = new Date(); start.setHours(0, 0, 0, 0);
    const end = new Date(); end.setHours(23, 59, 59, 999);
    const res = await ScheduleAPI.list(start.toISOString(), end.toISOString());
    todayEvents.value = res.data ?? [];
  } catch { /* 静默失败 */ }
  finally { scheduleLoading.value = false; }
});
</script>

<style scoped>
.panel-card { background: var(--semi-color-bg-1); border: 1px solid var(--semi-color-border); }
.panel-header { background: var(--semi-color-fill-0); }
.alert-tier-row:hover { background: var(--semi-color-fill-0); }
.ai-tool-arrow { opacity: 0; transform: translateX(-4px); transition: opacity 0.15s ease, transform 0.15s ease; }
.ai-tool-item:hover { background: var(--semi-color-fill-0); }
.ai-tool-item:hover .ai-tool-arrow { opacity: 1; transform: translateX(0); }
.schedule-item:hover { background: var(--semi-color-fill-0); }
</style>
