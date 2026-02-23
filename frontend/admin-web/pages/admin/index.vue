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
            128
          </h3>
          <p class="text-xs text-green-600 mt-2 flex items-center font-medium">
            <Icon name="material-symbols:trending-up" class="text-sm mr-1" />
            +12% 较上月
          </p>
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
            当前在线用户
          </p>
          <h3 class="text-2xl font-bold text-[var(--semi-color-text-0)] mt-1">
            2,451
          </h3>
          <p class="text-xs text-green-600 mt-2 flex items-center font-medium">
            <Icon name="material-symbols:trending-up" class="text-sm mr-1" />
            +5% 峰值
          </p>
        </div>
        <div class="p-2 bg-blue-100 rounded-lg">
          <Icon name="material-symbols:groups" class="text-blue-600 text-xl" />
        </div>
      </div>
      <!-- Stat Card 3 -->
      <div
        class="bg-[var(--semi-color-bg-0)] rounded-xl p-5 border border-[var(--semi-color-border)] shadow-sm flex items-start justify-between"
      >
        <div>
          <p
            class="text-xs font-semibold text-[var(--semi-color-text-2)] uppercase tracking-wide"
          >
            系统安全评分
          </p>
          <h3 class="text-2xl font-bold text-[var(--semi-color-text-0)] mt-1">
            98.5
          </h3>
          <p class="text-xs text-[var(--semi-color-text-2)] mt-2">
            上次扫描: 10分钟前
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
            8
          </h3>
          <p class="text-xs text-yellow-600 mt-2 flex items-center font-medium">
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

    <!-- Quick Actions Panel using Semi UI components could go here -->
  </div>
</template>

<script setup lang="ts">
import { definePageMeta } from "#imports";

definePageMeta({
  layout: "admin",
});
</script>
