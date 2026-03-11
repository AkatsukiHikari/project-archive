<template>
  <div class="flex flex-col gap-4 h-full">
    <!-- 左上：用户卡 -->
    <div
      class="rounded-2xl bg-[var(--semi-color-bg-0)] border border-[var(--semi-color-border)] shadow-sm overflow-hidden"
    >
      <!-- 渐变横幅 -->
      <div
        class="h-20 bg-gradient-to-r from-[oklch(var(--p)/0.8)] to-[oklch(var(--s)/0.6)]"
      />
      <!-- 头像 + 姓名 -->
      <div class="px-5 pb-5 -mt-10">
        <div class="relative w-fit mb-3 group">
          <!-- 白色底圆 + shadow，PNG 透明头像不穿帮 -->
          <div
            class="p-1 rounded-full bg-white shadow-md ring-4 ring-[var(--semi-color-bg-0)] cursor-pointer"
            @click="$emit('upload-avatar')"
          >
            <Avatar :src="avatarSrc || undefined" size="extra-large">
              {{ initial }}
            </Avatar>
          </div>
          <!-- Hover 相机遮罩 -->
          <div
            class="absolute inset-0 rounded-full bg-black/40 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity cursor-pointer"
            @click="$emit('upload-avatar')"
          >
            <Icon
              name="material-symbols:photo-camera"
              class="text-white text-lg"
            />
          </div>
          <!-- 上传中 spinner -->
          <div
            v-if="uploading"
            class="absolute inset-0 rounded-full bg-black/50 flex items-center justify-center"
          >
            <Spin size="small" />
          </div>
        </div>
        <p class="font-semibold text-[var(--semi-color-text-0)] text-sm">
          {{ displayName }}
        </p>
        <p class="text-xs text-[var(--semi-color-text-2)] mt-0.5">
          {{ jobTitle || "暂未设置职位" }}
        </p>
      </div>
    </div>

    <!-- 账户信息条 -->
    <div
      class="rounded-2xl bg-[var(--semi-color-bg-0)] border border-[var(--semi-color-border)] shadow-sm p-5"
    >
      <p
        class="text-xs font-semibold text-[var(--semi-color-text-2)] uppercase tracking-wide mb-3"
      >
        账户信息
      </p>
      <ul class="space-y-2.5 text-sm">
        <li class="flex items-center gap-2 text-[var(--semi-color-text-1)]">
          <Icon
            name="material-symbols:mail-outline"
            class="text-base shrink-0 text-[var(--semi-color-text-2)]"
          />
          <span class="truncate">{{ email || "-" }}</span>
        </li>
        <li class="flex items-center gap-2 text-[var(--semi-color-text-1)]">
          <Icon
            name="material-symbols:smartphone-outline"
            class="text-base shrink-0 text-[var(--semi-color-text-2)]"
          />
          <span>{{ phone || "未绑定手机" }}</span>
        </li>
        <li class="flex items-center gap-2 text-[var(--semi-color-text-1)]">
          <Icon
            name="material-symbols:apartment-outline"
            class="text-base shrink-0 text-[var(--semi-color-text-2)]"
          />
          <span>{{ orgDisplay }}</span>
        </li>
        <li class="flex items-center gap-2 text-[var(--semi-color-text-1)]">
          <Icon
            name="material-symbols:schedule-outline"
            class="text-base shrink-0 text-[var(--semi-color-text-2)]"
          />
          <span class="text-xs">{{ lastLoginDisplay }}</span>
        </li>
      </ul>
    </div>

    <!-- 角色标签 -->
    <div
      v-if="roles?.length"
      class="rounded-2xl bg-[var(--semi-color-bg-0)] border border-[var(--semi-color-border)] shadow-sm p-5"
    >
      <p
        class="text-xs font-semibold text-[var(--semi-color-text-2)] uppercase tracking-wide mb-3"
      >
        角色权限
      </p>
      <div class="flex flex-wrap gap-1.5">
        <Tag v-for="role in roles" :key="role.id" size="small" color="blue">
          {{ role.name }}
        </Tag>
      </div>
    </div>

    <!-- Tab 导航 -->
    <div
      class="rounded-2xl bg-[var(--semi-color-bg-0)] border border-[var(--semi-color-border)] shadow-sm overflow-hidden"
    >
      <button
        v-for="tab in TABS"
        :key="tab.key"
        class="w-full flex items-center gap-3 px-4 py-3 text-sm transition-colors border-l-2 text-left"
        :class="
          activeTab === tab.key
            ? 'border-[oklch(var(--p))] bg-[oklch(var(--p)/0.08)] text-[oklch(var(--p))] font-medium'
            : 'border-transparent text-[var(--semi-color-text-1)] hover:bg-[var(--semi-color-fill-0)]'
        "
        @click="$emit('switch-tab', tab.key)"
      >
        <Icon :name="tab.icon" class="text-base shrink-0" />
        {{ tab.label }}
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { Avatar, Spin, Tag } from "@kousum/semi-ui-vue";
import type { Role } from "@/api/iam";

interface Props {
  displayName: string;
  initial: string;
  jobTitle?: string;
  email?: string;
  phone?: string;
  orgDisplay: string;
  lastLoginDisplay: string;
  avatarSrc?: string;
  uploading?: boolean;
  roles?: Role[];
  activeTab: string;
}

const TABS = [
  { key: "basic", label: "基本设置", icon: "material-symbols:person-outline" },
  { key: "security", label: "安全管理", icon: "material-symbols:lock-outline" },
  { key: "todos", label: "待办任务", icon: "material-symbols:task-outline" },
  { key: "audit", label: "操作日志", icon: "material-symbols:history" },
];

defineProps<Props>();
defineEmits<{
  "upload-avatar": [];
  "switch-tab": [key: string];
}>();
</script>
