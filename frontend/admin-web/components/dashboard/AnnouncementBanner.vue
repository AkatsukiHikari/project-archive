<template>
  <Transition name="banner-slide">
    <div
      v-if="visible && current"
      class="announcement-banner rounded-xl px-5 py-3.5 flex items-start gap-3"
      :class="bannerClass"
    >
      <!-- 图标 -->
      <div class="shrink-0 mt-0.5">
        <Icon :name="bannerIcon" class="w-4 h-4" :class="iconClass" />
      </div>

      <!-- 内容 -->
      <div class="flex-1 min-w-0">
        <span class="text-[13px] font-semibold mr-2" :class="titleClass">
          {{ current.title }}
        </span>
        <span class="text-[12px] leading-relaxed" :class="contentClass">
          {{ current.content }}
        </span>
      </div>

      <!-- 右侧操作 -->
      <div class="flex items-center gap-3 shrink-0">
        <span class="text-[11px]" :class="timeClass">
          {{ formatTime(current.create_time) }}
        </span>
        <button
          class="dismiss-btn flex items-center justify-center w-5 h-5 rounded transition-colors duration-150 cursor-pointer"
          :class="dismissClass"
          @click="dismiss"
        >
          <Icon name="heroicons:x-mark" class="w-3.5 h-3.5" />
        </button>
      </div>
    </div>
  </Transition>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { getNotifications, markNotificationRead, type NotificationItem } from "@/api/notification";

const visible = ref(false);
const current = ref<NotificationItem | null>(null);

// ── 颜色策略 ─────────────────────────────────────────────────
const level = computed(() => current.value?.level ?? "info");

const bannerClass = computed(() => ({
  "banner-info":    level.value === "info",
  "banner-warning": level.value === "warning",
  "banner-error":   level.value === "error",
}));

const bannerIcon = computed(() => ({
  info:    "heroicons:information-circle",
  warning: "heroicons:exclamation-triangle",
  error:   "heroicons:x-circle",
}[level.value] ?? "heroicons:information-circle"));

const iconClass    = computed(() => ({ info: "text-primary",  warning: "text-warning",  error: "text-error"  }[level.value]));
const titleClass   = computed(() => ({ info: "text-primary",  warning: "text-warning",  error: "text-error"  }[level.value]));
const contentClass = computed(() => ({ info: "text-primary/70", warning: "text-warning/80", error: "text-error/80" }[level.value]));
const timeClass    = computed(() => ({ info: "text-primary/50", warning: "text-warning/60", error: "text-error/50" }[level.value]));
const dismissClass = computed(() => ({
  info:    "hover:bg-primary/10 text-primary/60",
  warning: "hover:bg-warning/10 text-warning/60",
  error:   "hover:bg-error/10 text-error/60",
}[level.value]));

// ── 时间格式化 ────────────────────────────────────────────────
function formatTime(iso: string): string {
  const d = new Date(iso);
  const now = new Date();
  const diffMs = now.getTime() - d.getTime();
  const diffH = Math.floor(diffMs / 3600000);
  if (diffH < 1)  return "刚刚";
  if (diffH < 24) return `${diffH}小时前`;
  const diffD = Math.floor(diffH / 24);
  if (diffD < 7)  return `${diffD}天前`;
  return d.toLocaleDateString("zh-CN", { month: "numeric", day: "numeric" });
}

// ── 关闭 ─────────────────────────────────────────────────────
async function dismiss() {
  visible.value = false;
  if (current.value) {
    try { await markNotificationRead(current.value.id); } catch { /* 静默 */ }
  }
}

// ── 拉取最新一条未读系统公告 ──────────────────────────────────
onMounted(async () => {
  try {
    const page = await getNotifications({ type: "system", page: 1, page_size: 10 });
    const unread = page.items.find((n) => !n.is_read);
    if (unread) {
      current.value = unread;
      visible.value = true;
    }
  } catch { /* 静默，公告不影响主界面 */ }
});
</script>

<style scoped>
.banner-info {
  background: oklch(var(--p) / 0.06);
  border: 1px solid oklch(var(--p) / 0.18);
}
.banner-warning {
  background: oklch(var(--wa) / 0.07);
  border: 1px solid oklch(var(--wa) / 0.22);
}
.banner-error {
  background: oklch(var(--er) / 0.06);
  border: 1px solid oklch(var(--er) / 0.20);
}

/* 滑入动画 */
.banner-slide-enter-active { transition: all 0.25s ease-out; }
.banner-slide-leave-active { transition: all 0.2s ease-in; }
.banner-slide-enter-from  { opacity: 0; transform: translateY(-8px); }
.banner-slide-leave-to    { opacity: 0; transform: translateY(-4px); }
</style>
