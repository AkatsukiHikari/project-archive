<template>
  <div class="panel-card">
    <div class="mb-4">
      <p class="panel-title">平台配置概览</p>
      <p class="panel-desc">当前系统基础配置状态</p>
    </div>

    <div v-if="loading" class="flex flex-col gap-3">
      <div v-for="i in 4" :key="i" class="skeleton-row" />
    </div>

    <div v-else class="flex flex-col gap-2">

      <!-- 存储方式 -->
      <div class="config-row">
        <div class="flex items-center gap-2">
          <Icon name="heroicons:server-stack" class="w-4 h-4 config-icon" />
          <span class="config-label">存储方式</span>
        </div>
        <span class="config-badge" :class="storageClass">{{ storageLabel }}</span>
      </div>

      <!-- 菜单数量 -->
      <div class="config-row">
        <div class="flex items-center gap-2">
          <Icon name="heroicons:list-bullet" class="w-4 h-4 config-icon" />
          <span class="config-label">菜单节点</span>
        </div>
        <span class="config-value">
          {{ cfg?.total_menu_visible ?? '—' }} 个可见
          <span class="config-muted">/ 共 {{ cfg?.total_menus ?? '—' }}</span>
        </span>
      </div>

      <!-- 按钮权限 -->
      <div class="config-row">
        <div class="flex items-center gap-2">
          <Icon name="heroicons:cursor-arrow-rays" class="w-4 h-4 config-icon" />
          <span class="config-label">按钮权限</span>
        </div>
        <span class="config-value">{{ cfg?.total_buttons ?? '—' }} 个</span>
      </div>

      <!-- 全局角色 -->
      <div class="config-row">
        <div class="flex items-center gap-2">
          <Icon name="heroicons:shield-check" class="w-4 h-4 config-icon" />
          <span class="config-label">全局角色</span>
        </div>
        <span class="config-value">{{ cfg?.total_roles ?? '—' }} 个</span>
      </div>

      <!-- 租户总数 -->
      <div class="config-row">
        <div class="flex items-center gap-2">
          <Icon name="heroicons:building-storefront" class="w-4 h-4 config-icon" />
          <span class="config-label">租户总数</span>
        </div>
        <span class="config-value">{{ cfg?.total_tenants ?? '—' }} 个</span>
      </div>

    </div>

    <!-- 快捷操作 -->
    <div class="mt-5 pt-4 border-t border-[var(--semi-color-border)]">
      <p class="text-[11px] font-semibold uppercase tracking-wide mb-3" style="color: var(--semi-color-text-2)">快捷操作</p>
      <div class="grid grid-cols-2 gap-2">
        <NuxtLink
          v-for="link in quickLinks"
          :key="link.path"
          :to="link.path"
          class="quick-link"
        >
          <Icon :name="link.icon" class="w-4 h-4" />
          {{ link.label }}
        </NuxtLink>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import type { PlatformConfig } from "@/api/iam";
import { StatsAPI } from "@/api/iam";

const cfg = ref<PlatformConfig | null>(null);
const loading = ref(true);

const STORAGE_LABELS: Record<string, string> = {
  local: "本地磁盘",
  minio: "MinIO",
  aws: "AWS S3",
  alioss: "阿里云 OSS",
};

const storageLabel = computed(() => STORAGE_LABELS[cfg.value?.storage_type ?? ""] ?? cfg.value?.storage_type ?? "—");
const storageClass = computed(() => {
  const t = cfg.value?.storage_type;
  if (t === "minio") return "badge-blue";
  if (t === "aws" || t === "alioss") return "badge-green";
  return "badge-gray";
});

const quickLinks = [
  { label: "用户管理", path: "/admin/users",         icon: "heroicons:users" },
  { label: "角色配置", path: "/admin/roles",         icon: "heroicons:shield-check" },
  { label: "菜单管理", path: "/admin/menus",         icon: "heroicons:list-bullet" },
  { label: "审计日志", path: "/admin/audit",         icon: "heroicons:clipboard-document-list" },
  { label: "SSO 集成", path: "/admin/sso",           icon: "heroicons:key" },
  { label: "组织架构", path: "/admin/organizations", icon: "heroicons:building-office-2" },
];

onMounted(async () => {
  try {
    const res = await StatsAPI.platformConfig() as any;
    cfg.value = res.data ?? null;
  } catch {
    // 静默失败，面板显示 —
  } finally {
    loading.value = false;
  }
});
</script>

<style scoped>
.panel-card {
  background: var(--semi-color-bg-0);
  border: 1px solid var(--semi-color-border);
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 1px 3px rgba(0,0,0,.04);
  height: 100%;
}
.panel-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--semi-color-text-0);
}
.panel-desc {
  font-size: 11px;
  color: var(--semi-color-text-2);
  margin-top: 2px;
}
.config-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 7px 10px;
  border-radius: 8px;
  background: var(--semi-color-fill-0);
}
.config-icon { color: var(--semi-color-text-2); }
.config-label {
  font-size: 13px;
  color: var(--semi-color-text-1);
}
.config-value {
  font-size: 13px;
  font-weight: 500;
  color: var(--semi-color-text-0);
}
.config-muted {
  font-size: 11px;
  color: var(--semi-color-text-2);
  font-weight: 400;
}
.config-badge {
  font-size: 11px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 6px;
}
.badge-blue  { background: rgba(59,130,246,0.1);  color: #3b82f6; }
.badge-green { background: rgba(16,185,129,0.1);  color: #10b981; }
.badge-gray  { background: var(--semi-color-fill-1); color: var(--semi-color-text-1); }

.quick-link {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 7px 10px;
  border-radius: 8px;
  font-size: 12px;
  color: var(--semi-color-text-1);
  background: var(--semi-color-fill-0);
  border: 1px solid transparent;
  text-decoration: none;
  transition: all 0.15s;
}
.quick-link:hover {
  background: var(--semi-color-primary-light-default);
  border-color: var(--semi-color-primary-light-hover);
  color: var(--semi-color-primary);
}
.skeleton-row {
  height: 36px;
  border-radius: 8px;
  background: var(--semi-color-fill-0);
  animation: pulse 1.2s ease-in-out infinite;
}
@keyframes pulse { 0%,100%{ opacity:1 } 50%{ opacity:.4 } }
</style>
