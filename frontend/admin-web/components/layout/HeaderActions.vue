<template>
  <div class="flex items-center gap-2">
    <!-- 时间 -->
    <div
      class="hidden lg:flex flex-col items-end mr-3 border-r border-base-300 pr-4"
    >
      <span class="text-sm font-semibold text-base-content tabular-nums">
        {{ currentTime }}
      </span>
      <span class="text-xs text-base-content/50">{{ currentDate }}</span>
    </div>

    <!-- 主题切换 -->
    <div class="dropdown dropdown-end">
      <div
        tabindex="0"
        role="button"
        class="btn btn-ghost btn-circle btn-sm"
        title="切换主题"
      >
        <SwatchIcon class="w-5 h-5" />
      </div>
      <div
        tabindex="0"
        class="dropdown-content z-[60] mt-3 p-3 shadow-xl bg-base-100 rounded-xl w-48 border border-base-300"
      >
        <div class="text-xs font-semibold text-base-content/60 mb-2 px-1">
          选择主题
        </div>
        <div class="flex flex-col gap-1">
          <button
            v-for="theme in themes"
            :key="theme.name"
            class="flex items-center gap-3 px-2 py-2 rounded-lg text-sm transition-colors hover:bg-base-200"
            :class="{
              'bg-primary/10 text-primary font-medium':
                currentTheme === theme.name,
            }"
            @click="setTheme(theme.name)"
          >
            <div class="flex gap-0.5">
              <span
                v-for="(color, i) in theme.colors"
                :key="i"
                class="w-2.5 h-2.5 rounded-full ring-1 ring-base-300"
                :style="{ backgroundColor: color }"
              />
            </div>
            <span>{{ theme.label }}</span>
            <CheckCircleSolid
              v-if="currentTheme === theme.name"
              class="w-4 h-4 ml-auto text-primary"
            />
          </button>
        </div>
      </div>
    </div>

    <!-- 通知 -->
    <div class="dropdown dropdown-end">
      <div
        tabindex="0"
        role="button"
        class="btn btn-ghost btn-circle btn-sm relative"
        title="通知"
      >
        <BellIcon class="w-5 h-5" />
        <span
          v-if="unreadCount > 0"
          class="absolute -top-0.5 -right-0.5 min-w-[18px] h-[18px] flex items-center justify-center rounded-full bg-error text-error-content text-[10px] font-bold px-1 ring-2 ring-base-100"
        >
          {{ unreadCount > 99 ? "99+" : unreadCount }}
        </span>
      </div>
      <div
        tabindex="0"
        class="dropdown-content z-[60] mt-3 shadow-xl bg-base-100 rounded-xl w-[380px] border border-base-300 overflow-hidden"
      >
        <!-- 通知头部 -->
        <div
          class="flex items-center justify-between px-4 py-3 border-b border-base-300"
        >
          <h3 class="text-sm font-bold text-base-content">通知中心</h3>
          <button
            v-if="unreadCount > 0"
            class="text-xs text-primary hover:text-primary-focus transition-colors"
            @click="markAllRead"
          >
            全部已读
          </button>
        </div>

        <!-- Tab 切换 -->
        <div role="tablist" class="tabs tabs-bordered bg-base-100">
          <button
            role="tab"
            class="tab tab-sm"
            :class="{ 'tab-active': activeTab === 'all' }"
            @click="activeTab = 'all'"
          >
            全部
            <span
              v-if="unreadCount > 0"
              class="badge badge-xs badge-primary ml-1"
              >{{ unreadCount }}</span
            >
          </button>
          <button
            role="tab"
            class="tab tab-sm"
            :class="{ 'tab-active': activeTab === 'todo' }"
            @click="activeTab = 'todo'"
          >
            待办
          </button>
          <button
            role="tab"
            class="tab tab-sm"
            :class="{ 'tab-active': activeTab === 'system' }"
            @click="activeTab = 'system'"
          >
            系统
          </button>
        </div>

        <!-- 通知列表 -->
        <div class="max-h-[360px] overflow-y-auto">
          <!-- 空状态 -->
          <div
            v-if="filteredNotifications.length === 0"
            class="flex flex-col items-center justify-center py-12 text-base-content/40"
          >
            <BellSlashIcon class="w-10 h-10 mb-2" />
            <span class="text-sm">暂无通知</span>
          </div>

          <!-- 通知项 -->
          <div
            v-for="notification in filteredNotifications"
            :key="notification.id"
            class="flex gap-3 px-4 py-3 border-b border-base-200 last:border-0 hover:bg-base-200/50 transition-colors cursor-pointer"
            :class="{ 'bg-primary/5': !notification.is_read }"
            @click="markAsRead(notification.id)"
          >
            <!-- 图标 -->
            <div
              class="flex-shrink-0 w-9 h-9 rounded-full flex items-center justify-center"
              :class="
                notificationIconClass(notification.type, notification.level)
              "
            >
              <component
                :is="notificationIcon(notification.type)"
                class="w-4 h-4"
              />
            </div>
            <!-- 内容 -->
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2">
                <span class="text-sm font-medium text-base-content truncate">
                  {{ notification.title }}
                </span>
                <span
                  v-if="!notification.is_read"
                  class="w-2 h-2 rounded-full bg-primary flex-shrink-0"
                />
              </div>
              <p class="text-xs text-base-content/60 mt-0.5 line-clamp-2">
                {{ notification.content }}
              </p>
              <span class="text-[10px] text-base-content/40 mt-1 block">
                {{ formatTime(notification.create_time) }}
              </span>
            </div>
          </div>
        </div>

        <!-- 底部 -->
        <div class="border-t border-base-300 px-4 py-2.5">
          <NuxtLink
            to="/notifications"
            class="block text-center text-xs text-primary hover:text-primary-focus font-medium transition-colors"
          >
            查看全部通知
          </NuxtLink>
        </div>
      </div>
    </div>

    <!-- 用户头像 -->
    <div class="dropdown dropdown-end">
      <div
        tabindex="0"
        role="button"
        class="flex items-center gap-3 pl-2 cursor-pointer hover:opacity-80 transition-opacity"
      >
        <img
          alt="用户头像"
          class="h-9 w-9 rounded-full object-cover border-2 border-[var(--semi-color-border)] shadow-sm bg-[var(--semi-color-fill-0)]"
          :src="userStore.userInfo?.avatar || ''"
        />
        <div class="hidden md:block text-left">
          <div class="text-sm font-medium text-base-content">
            {{ userStore.userInfo?.username || "系统管理员" }}
          </div>
          <div class="text-xs text-base-content/50">超级管理员</div>
        </div>
      </div>
      <ul
        tabindex="0"
        class="dropdown-content z-[60] menu p-2 shadow-lg bg-base-100 rounded-xl w-52 mt-3 border border-base-300"
      >
        <li>
          <NuxtLink to="/admin/profile" class="text-sm flex items-center gap-2">
            <UserIcon class="w-4 h-4" /> 个人中心
          </NuxtLink>
        </li>
        <li>
          <a class="text-sm"> <Cog6ToothIcon class="w-4 h-4" /> 系统设置 </a>
        </li>
        <div class="divider my-1" />
        <li>
          <a class="text-sm text-error" @click="handleLogout">
            <ArrowRightOnRectangleIcon class="w-4 h-4" />
            退出登录
          </a>
        </li>
      </ul>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from "vue";
import type { Component } from "vue";
import { useUserStore } from "@/stores/user";
import { useAuth } from "@/hooks/useAuth";
import { useTheme } from "@/hooks/useTheme";
import { CheckCircleIcon as CheckCircleSolid } from "@heroicons/vue/24/solid";
import {
  SwatchIcon,
  BellIcon,
  BellSlashIcon,
  MegaphoneIcon,
  ClipboardDocumentCheckIcon,
  ChatBubbleLeftEllipsisIcon,
  UserIcon,
  Cog6ToothIcon,
  ArrowRightOnRectangleIcon,
} from "@heroicons/vue/24/outline";
import {
  getNotifications,
  getUnreadCount,
  markNotificationRead,
  markAllNotificationsRead,
  type NotificationItem,
} from "@/api/notification";

const userStore = useUserStore();
const { logout: handleLogout } = useAuth();
const { currentTheme, themes, setTheme } = useTheme();

// ─── 实时时间 ───
const currentTime = ref("");
const currentDate = ref("");

const updateTime = () => {
  const now = new Date();
  currentTime.value = now.toLocaleTimeString("zh-CN", {
    hour: "2-digit",
    minute: "2-digit",
  });
  currentDate.value = now.toLocaleDateString("zh-CN", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });
};

let timer: ReturnType<typeof setInterval>;
onMounted(() => {
  updateTime();
  timer = setInterval(updateTime, 30000);
  fetchNotifications();
  fetchUnreadCount();
});
onUnmounted(() => clearInterval(timer));

// ─── 通知系统 ───
const activeTab = ref<"all" | "todo" | "system">("all");
const notifications = ref<NotificationItem[]>([]);
const unreadCount = ref(0);

const filteredNotifications = computed(() => {
  if (activeTab.value === "all") return notifications.value;
  return notifications.value.filter((n) => n.type === activeTab.value);
});

function notificationIcon(type: string): Component {
  const icons: Record<string, Component> = {
    system: MegaphoneIcon,
    todo: ClipboardDocumentCheckIcon,
    message: ChatBubbleLeftEllipsisIcon,
  };
  return icons[type] || BellIcon;
}

function notificationIconClass(type: string, level: string): string {
  if (level === "error") return "bg-error/10 text-error";
  if (level === "warning") return "bg-warning/10 text-warning";
  if (type === "todo") return "bg-info/10 text-info";
  return "bg-primary/10 text-primary";
}

function formatTime(dateStr: string): string {
  if (!dateStr) return "";
  const date = new Date(dateStr);
  const now = new Date();
  const diff = now.getTime() - date.getTime();
  const minutes = Math.floor(diff / 60000);
  if (minutes < 1) return "刚刚";
  if (minutes < 60) return `${minutes} 分钟前`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours} 小时前`;
  const days = Math.floor(hours / 24);
  if (days < 7) return `${days} 天前`;
  return date.toLocaleDateString("zh-CN");
}

async function fetchNotifications() {
  try {
    const typeParam = activeTab.value === "all" ? undefined : activeTab.value;
    const data = await getNotifications({
      type: typeParam,
      page: 1,
      page_size: 20,
    });
    notifications.value = data.items;
  } catch {
    notifications.value = [];
  }
}

async function fetchUnreadCount() {
  try {
    unreadCount.value = await getUnreadCount();
  } catch {
    unreadCount.value = 0;
  }
}

async function markAsRead(id: string) {
  const notification = notifications.value.find((n) => n.id === id);
  if (notification && !notification.is_read) {
    try {
      await markNotificationRead(id);
      notification.is_read = true;
      unreadCount.value = Math.max(0, unreadCount.value - 1);
    } catch {
      return; // 静默失败
    }
  }
}

async function markAllRead() {
  try {
    await markAllNotificationsRead();
    notifications.value.forEach((n) => (n.is_read = true));
    unreadCount.value = 0;
  } catch {
    return; // 静默失败
  }
}

watch(activeTab, () => {
  fetchNotifications();
});
</script>
