<template>
  <div class="space-y-6">
    <!-- Dashboard Overview Cards -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
      <!-- Stat Card 1 -->
      <div
        class="bg-[var(--semi-color-bg-0)] rounded-xl p-5 border border-[var(--semi-color-border)] shadow-sm flex items-start justify-between"
      >
        <div>
          <p
            class="text-xs font-semibold text-[var(--semi-color-text-2)] uppercase tracking-wide"
          >
            活跃租户总数
          </p>
          <h3 class="text-2xl font-bold text-[var(--semi-color-text-0)] mt-1">
            {{ stats?.active_tenants ?? "—" }}
          </h3>
        </div>
        <div class="p-2 bg-blue-100 rounded-lg">
          <Icon
            name="material-symbols:apartment"
            class="text-blue-600 text-xl"
          />
        </div>
      </div>
      <!-- Stat Card 2 -->
      <div
        class="bg-[var(--semi-color-bg-0)] rounded-xl p-5 border border-[var(--semi-color-border)] shadow-sm flex items-start justify-between"
      >
        <div>
          <p
            class="text-xs font-semibold text-[var(--semi-color-text-2)] uppercase tracking-wide"
          >
            活跃用户数
          </p>
          <h3 class="text-2xl font-bold text-[var(--semi-color-text-0)] mt-1">
            {{ stats?.active_users ?? "—" }}
          </h3>
          <p
            v-if="stats"
            class="text-xs text-[var(--semi-color-text-2)] mt-2"
          >
            共 {{ stats.total_users }} 个账号
          </p>
        </div>
        <div class="p-2 bg-blue-100 rounded-lg">
          <Icon name="material-symbols:groups" class="text-blue-600 text-xl" />
        </div>
      </div>
      <!-- Stat Card 3 - placeholder for future system health metric -->
      <div
        class="bg-[var(--semi-color-bg-0)] rounded-xl p-5 border border-[var(--semi-color-border)] shadow-sm flex items-start justify-between"
      >
        <div>
          <p
            class="text-xs font-semibold text-[var(--semi-color-text-2)] uppercase tracking-wide"
          >
            系统状态
          </p>
          <h3 class="text-2xl font-bold text-[var(--semi-color-text-0)] mt-1">
            正常
          </h3>
          <p class="text-xs text-[var(--semi-color-text-2)] mt-2">
            所有服务运行中
          </p>
        </div>
        <div class="p-2 bg-green-100 rounded-lg">
          <Icon
            name="material-symbols:verified-user"
            class="text-green-600 text-xl"
          />
        </div>
      </div>
      <!-- Stat Card 4 -->
      <div
        class="bg-[var(--semi-color-bg-0)] rounded-xl p-5 border border-[var(--semi-color-border)] shadow-sm flex items-start justify-between"
      >
        <div>
          <p
            class="text-xs font-semibold text-[var(--semi-color-text-2)] uppercase tracking-wide"
          >
            待处理审批
          </p>
          <h3 class="text-2xl font-bold text-[var(--semi-color-text-0)] mt-1">
            {{ stats?.pending_sips ?? "—" }}
          </h3>
          <p
            v-if="stats && stats.pending_sips > 0"
            class="text-xs text-yellow-600 mt-2 flex items-center font-medium"
          >
            <Icon name="material-symbols:priority-high" class="text-sm mr-1" />
            需尽快处理
          </p>
        </div>
        <div class="p-2 bg-yellow-100 rounded-lg">
          <Icon
            name="material-symbols:pending-actions"
            class="text-yellow-600 text-xl"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { service } from "@/utils/axios/service";

definePageMeta({
  layout: "admin",
});

interface DashboardStats {
  active_tenants: number;
  total_users: number;
  active_users: number;
  pending_sips: number;
}

const stats = ref<DashboardStats | null>(null);

onMounted(async () => {
  try {
    const res = await service.get<{ code: number; data: DashboardStats }>(
      "/api/v1/stats/dashboard"
    );
    if (res.data.code === 0) {
      stats.value = res.data.data;
    }
  } catch {
    // stats remain null — cards show "—"
  }
});
</script>
