<template>
  <div class="flex flex-col gap-5">

    <!-- 欢迎栏 -->
    <div class="welcome-bar">
      <div>
        <h2 class="welcome-title">{{ greeting }}，{{ displayName }}</h2>
        <p class="welcome-date">{{ todayStr }} · 平台基础管理控制台</p>
      </div>
      <div v-if="stats && stats.new_users_today > 0" class="badge-chip chip-blue">
        <Icon name="heroicons:user-plus" class="w-3.5 h-3.5" />
        今日新增 {{ stats.new_users_today }} 名用户
      </div>
    </div>

    <!-- KPI 卡片行 -->
    <div class="grid grid-cols-2 lg:grid-cols-4 gap-4">
      <!-- IAM 卡片 -->
      <KpiCard
        label="系统用户"
        :value="stats?.total_users ?? '—'"
        :sub="stats ? `活跃 ${stats.active_users} 人` : ''"
        icon="heroicons:users"
        icon-bg="rgba(59,130,246,0.1)"
        icon-color="#3b82f6"
        :loading="statsLoading"
      />
      <KpiCard
        label="组织部门"
        :value="stats?.total_orgs ?? '—'"
        icon="heroicons:building-office-2"
        icon-bg="rgba(245,158,11,0.1)"
        icon-color="#f59e0b"
        :loading="statsLoading"
      />
      <!-- 存储层 KPI（超管可见） -->
      <KpiCard
        v-if="isSuperAdmin"
        label="MinIO 对象总数"
        :value="(stats?.minio_objects ?? -1) >= 0 ? (stats?.minio_objects ?? '—') : '—'"
        :sub="(stats?.minio_size_gb ?? -1) >= 0 ? `${stats?.minio_size_gb ?? ''} GB` : ''"
        icon="heroicons:server-stack"
        icon-bg="rgba(16,185,129,0.1)"
        icon-color="#10b981"
        :loading="statsLoading"
      />
      <KpiCard
        v-if="isSuperAdmin"
        label="数据库连接"
        :value="(stats?.pg_connections ?? -1) >= 0 ? (stats?.pg_connections ?? '—') : '—'"
        :sub="(stats?.redis_memory_mb ?? -1) >= 0 ? `Redis ${stats?.redis_memory_mb ?? ''} MB` : ''"
        icon="heroicons:circle-stack"
        icon-bg="rgba(139,92,246,0.1)"
        icon-color="#8b5cf6"
        :loading="statsLoading"
      />
      <!-- 非超管补位 -->
      <KpiCard
        v-if="!isSuperAdmin"
        label="全局角色"
        :value="userStore.roles.length"
        icon="heroicons:shield-check"
        icon-bg="rgba(139,92,246,0.1)"
        icon-color="#8b5cf6"
      />
      <KpiCard
        v-if="!isSuperAdmin"
        label="活跃租户"
        :value="(stats?.active_tenants ?? -1) >= 0 ? (stats?.active_tenants ?? '—') : '—'"
        icon="heroicons:building-storefront"
        icon-bg="rgba(16,185,129,0.1)"
        icon-color="#10b981"
        :loading="statsLoading"
      />
    </div>

    <!-- 存储组件详情（仅超管） -->
    <template v-if="isSuperAdmin">
      <div class="section-header">
        <p class="section-title">存储基础设施</p>
        <button class="refresh-btn" :class="{ spinning: storageLoading }" @click="loadStorage">
          <Icon name="heroicons:arrow-path" class="w-3.5 h-3.5" />
          刷新
        </button>
      </div>

      <div v-if="storageLoading && !storageComponents.length" class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        <div v-for="i in 5" :key="i" class="skeleton-card" />
      </div>

      <div v-else class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        <StorageComponentCard
          v-for="comp in storageComponents"
          :key="comp.type"
          :component="comp"
        />
      </div>
    </template>

    <!-- 平台配置快照（仅超管） -->
    <PlatformStatusPanel v-if="isSuperAdmin" />

  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { useUserStore } from "@/stores/user";
import type { DashboardStats, StorageComponent } from "@/api/iam";
import { StatsAPI } from "@/api/iam";
import KpiCard from "@/components/admin/dashboard/KpiCard.vue";
import StorageComponentCard from "@/components/admin/dashboard/StorageComponentCard.vue";
import PlatformStatusPanel from "@/components/admin/dashboard/PlatformStatusPanel.vue";

definePageMeta({ layout: "admin", middleware: "auth" });

const userStore = useUserStore();

const isSuperAdmin = computed(() => userStore.userInfo?.is_superadmin ?? false);
const displayName = computed(() =>
  userStore.userInfo?.full_name || userStore.userInfo?.username || "管理员"
);

const greeting = computed(() => {
  const h = new Date().getHours();
  if (h < 6)  return "夜深了";
  if (h < 12) return "早上好";
  if (h < 14) return "中午好";
  if (h < 18) return "下午好";
  return "晚上好";
});

const todayStr = computed(() =>
  new Date().toLocaleDateString("zh-CN", {
    year: "numeric", month: "long", day: "numeric", weekday: "long",
  })
);

// KPI 数据
const stats = ref<DashboardStats | null>(null);
const statsLoading = ref(true);

// 存储组件详情
const storageComponents = ref<StorageComponent[]>([]);
const storageLoading = ref(false);

async function loadStorage() {
  storageLoading.value = true;
  try {
    const res = await StatsAPI.storage() as any;
    storageComponents.value = res.data?.components ?? [];
  } catch {
    // 静默失败
  } finally {
    storageLoading.value = false;
  }
}

onMounted(async () => {
  // KPI 和存储详情并发加载
  const tasks: Promise<void>[] = [
    StatsAPI.dashboard().then((res: any) => {
      stats.value = res.data ?? null;
    }).catch(() => {}).finally(() => { statsLoading.value = false; }),
  ];

  if (isSuperAdmin.value) {
    tasks.push(loadStorage());
  } else {
    statsLoading.value = false;
  }

  await Promise.allSettled(tasks);
});
</script>

<style scoped>
.welcome-bar {
  background: var(--semi-color-bg-0);
  border: 1px solid var(--semi-color-border);
  border-radius: 12px;
  padding: 20px 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
}
.welcome-title {
  font-size: 18px;
  font-weight: 700;
  color: var(--semi-color-text-0);
}
.welcome-date {
  font-size: 12px;
  color: var(--semi-color-text-2);
  margin-top: 3px;
}
.badge-chip {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 5px 12px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 500;
}
.chip-blue { background: rgba(59,130,246,0.1); color: #3b82f6; }

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.section-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--semi-color-text-0);
}
.refresh-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 5px 10px;
  border-radius: 7px;
  border: 1px solid var(--semi-color-border);
  background: transparent;
  font-size: 12px;
  color: var(--semi-color-text-1);
  cursor: pointer;
  transition: background 0.15s;
}
.refresh-btn:hover { background: var(--semi-color-fill-0); }
.refresh-btn.spinning svg { animation: spin 0.8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

.skeleton-card {
  height: 180px;
  border-radius: 12px;
  background: var(--semi-color-fill-0);
  animation: pulse 1.2s ease-in-out infinite;
}
@keyframes pulse { 0%,100%{ opacity:1 } 50%{ opacity:.4 } }
</style>
