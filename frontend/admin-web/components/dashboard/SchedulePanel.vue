<template>
  <div
    class="bg-base-100 border border-base-content/10 rounded-2xl shadow-sm overflow-hidden flex flex-col h-full relative"
    ref="panelRef"
  >
    <!-- 取消头部的重复标题，直接展示日历内容 -->
    <div
      class="p-4 flex items-center justify-between border-b border-base-content/5 bg-base-200/30"
    >
      <div class="text-xs font-semibold text-base-content/70 uppercase">
        本月排期概览
      </div>
      <NuxtLink to="/schedule" class="btn btn-xs btn-ghost text-primary">
        全景日历
        <Icon
          name="heroicons:arrow-top-right-on-square"
          class="w-3 h-3 ml-0.5"
        />
      </NuxtLink>
    </div>

    <div class="flex-1 flex flex-col p-4 bg-base-100 min-h-[400px]">
      <client-only>
        <!-- events-on-month-view 强制在月视图渲染事件，而不是显示总数 ① -->
        <vue-cal
          xsmall
          active-view="month"
          events-on-month-view="short"
          :disable-views="['years', 'year', 'week', 'day']"
          hide-view-selector
          class="vuecal--blue-theme !h-[260px] mb-2 border-none shadow-none custom-mini-cal"
          locale="zh-cn"
          :events="calendarEvents"
          @event-mouse-enter="onEventMouseEnter"
          @event-mouse-leave="onEventMouseLeave"
          @event-click="onEventClick"
        >
          <!-- 自定义事件渲染：将其渲染为一个跟随主题色的小圆点 -->
          <template #event="{ event }">
            <div class="flex justify-center mt-[1px]">
              <div
                class="w-1 h-1 rounded-full"
                :class="{
                  'bg-primary': event.event_type === 'meeting',
                  'bg-warning': event.event_type === 'audit',
                  'bg-info': !['meeting', 'audit'].includes(event.event_type),
                }"
              ></div>
            </div>
          </template>
        </vue-cal>
      </client-only>

      <!-- 自定义悬浮气泡 (Hover Popover) -->
      <div
        v-if="hoverEvent"
        class="absolute z-[100] bg-base-100 border border-base-content/10 shadow-xl rounded-xl p-3 w-48 text-left pointer-events-none transition-opacity duration-200"
        :style="{ top: hoverPos.y + 'px', left: hoverPos.x + 'px' }"
      >
        <div class="text-xs font-bold text-base-content mb-1 truncate">
          {{ hoverEvent.title }}
        </div>
        <div class="text-[10px] text-base-content/60 flex items-center gap-1">
          <Icon name="heroicons:clock" class="w-3 h-3" />
          {{ hoverEvent.start.substring(11, 16) }} -
          {{ hoverEvent.end.substring(11, 16) }}
        </div>
        <div
          class="text-[10px] text-base-content/60 flex items-center gap-1 mt-0.5 truncate bg-base-200/50 p-1 rounded"
        >
          <Icon name="heroicons:tag" class="w-3 h-3" />
          类型:
          {{
            hoverEvent.event_type === "meeting"
              ? "会议"
              : hoverEvent.event_type === "audit"
                ? "审查"
                : "普通任务"
          }}
        </div>
      </div>

      <div class="divider my-1"></div>

      <!-- 详细日程列表 -->
      <div class="flex-1 overflow-y-auto">
        <div v-if="loading" class="flex justify-center items-center py-4">
          <span class="loading loading-spinner text-primary loading-sm"></span>
        </div>

        <div
          v-else-if="upcomingSchedules.length === 0"
          class="flex flex-col items-center justify-center text-base-content/40 py-4 h-full"
        >
          <p class="text-xs">近期暂无紧迫日程或会议</p>
        </div>

        <div v-else class="space-y-3 mt-2">
          <h4
            class="text-[10px] font-bold text-base-content/40 uppercase tracking-wider mb-2"
          >
            即将到来
          </h4>
          <div
            v-for="item in upcomingSchedules"
            :key="item.id"
            class="relative pl-3 border-l-[3px] py-1 transition-colors hover:bg-base-200/50 rounded-r-lg group cursor-pointer"
            :class="{
              'border-primary': item.event_type === 'meeting',
              'border-warning': item.event_type === 'audit',
              'border-info': !['meeting', 'audit'].includes(item.event_type),
            }"
            @click="$router.push('/schedule')"
          >
            <div class="flex items-start justify-between">
              <div class="flex-1">
                <h4
                  class="text-xs font-semibold text-base-content group-hover:text-primary transition-colors truncate pr-2"
                >
                  {{ item.title }}
                </h4>
                <div
                  class="text-[11px] text-base-content/50 mt-1 flex items-center gap-2"
                >
                  <span>{{ formatTime(item.start_time) }}</span>
                  <span
                    v-if="item.location"
                    class="truncate max-w-[90px] inline-flex items-center gap-0.5"
                  >
                    <Icon name="heroicons:map-pin" class="w-3 h-3" />
                    {{ item.location }}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from "vue";
import { useRouter } from "vue-router";
import { ScheduleAPI, type ScheduleEvent } from "@/api/schedule";
import VueCal from "vue-cal";
import "vue-cal/dist/vuecal.css";

const router = useRouter();
const schedules = ref<ScheduleEvent[]>([]);
const loading = ref(true);
const panelRef = ref<HTMLElement | null>(null);

// Popover 状态
const hoverEvent = ref<any>(null);
const hoverPos = ref({ x: 0, y: 0 });

const onEventMouseEnter = (event: any, e: MouseEvent) => {
  hoverEvent.value = event;
  const target = e.currentTarget as HTMLElement;

  if (panelRef.value && target) {
    const parentRect = panelRef.value.getBoundingClientRect();
    const targetRect = target.getBoundingClientRect();

    // 把气泡定在小格子附近
    hoverPos.value = {
      x: targetRect.left - parentRect.left - 192 / 2 + targetRect.width / 2,
      y: targetRect.top - parentRect.top - 70,
    };
  }
};

const onEventMouseLeave = () => {
  hoverEvent.value = null;
};

const onEventClick = (event: any, e: Event) => {
  e.stopPropagation();
  router.push("/schedule");
};

// 剔除了假的节假日，完全依赖后端数据。并支持日历按实际数据打点
const calendarEvents = computed(() => {
  return schedules.value.map((e) => ({
    start: e.start_time.slice(0, 16).replace("T", " "),
    end: e.end_time.slice(0, 16).replace("T", " "),
    title: e.title,
    event_type: e.event_type,
  }));
});

// 仅在列表中列出即将到来的日程，日历显示所有
const upcomingSchedules = computed(() => {
  const now = new Date();
  return schedules.value
    .filter((e) => new Date(e.start_time) > now || new Date(e.end_time) > now)
    .slice(0, 6);
});

const formatTime = (isoString: string) => {
  const d = new Date(isoString);
  const today = new Date();

  if (d.toDateString() === today.toDateString()) {
    return `今天 ${d.getHours().toString().padStart(2, "0")}:${d.getMinutes().toString().padStart(2, "0")}`;
  }

  const tomorrow = new Date(today);
  tomorrow.setDate(today.getDate() + 1);
  if (d.toDateString() === tomorrow.toDateString()) {
    return `明天 ${d.getHours().toString().padStart(2, "0")}:${d.getMinutes().toString().padStart(2, "0")}`;
  }

  return `${d.getMonth() + 1}月${d.getDate()}日 ${d.getHours().toString().padStart(2, "0")}:${d.getMinutes().toString().padStart(2, "0")}`;
};

onMounted(async () => {
  loading.value = true;
  try {
    // 获取当月（或者全部关联）真实日程数据，不传入todayStr，获取历史也能在日历标点
    const res = await ScheduleAPI.list();
    schedules.value = res.data;
  } catch (error) {
    console.error("Failed to fetch dashboard schedules", error);
  } finally {
    loading.value = false;
  }
});
</script>

<style>
/* 完全隐藏默认的数量气泡 ① */
.custom-mini-cal .vuecal__cell-events-count {
  display: none !important;
}

/* 隐藏 vue-cal 自带的事件背景块和文字，只用我们 #event 插槽渲染的小圆点 */
.custom-mini-cal .vuecal__event {
  background-color: transparent !important;
  box-shadow: none !important;
  color: transparent !important;
  cursor: pointer;
}
.custom-mini-cal .vuecal__event-title,
.custom-mini-cal .vuecal__event-content {
  display: none !important;
}

/* 简约风表格去边框 */
.custom-mini-cal .vuecal__cell {
  border: none;
}
.custom-mini-cal .vuecal__title-bar {
  background-color: transparent !important;
  border: none;
}
.custom-mini-cal .vuecal__heading {
  font-size: 11px;
  color: oklch(var(--bc) / 0.5);
  padding-bottom: 4px;
}
.custom-mini-cal .vuecal__cell--today,
.custom-mini-cal .vuecal__cell--current {
  background-color: oklch(var(--bc) / 0.03) !important;
  border-radius: 4px;
}
</style>
