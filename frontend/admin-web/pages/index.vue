<template>
  <div class="space-y-8">
    <!-- 核心应用 -->
    <section aria-label="核心应用">
      <CommonSectionTitle title="核心应用" class="mb-6" />
      <DashboardAppCardGrid :apps="coreApps" />
    </section>

    <!-- 工作台 + 关键指标 -->
    <div class="grid grid-cols-1 lg:grid-cols-12 gap-8">
      <!-- 左侧：工作台 -->
      <div class="lg:col-span-8 flex flex-col">
        <CommonSectionTitle title="工作台" class="mb-6" />
        <DashboardWorkbenchPanel />
      </div>

      <!-- 右侧：关键指标 -->
      <div class="lg:col-span-4 flex flex-col">
        <CommonSectionTitle title="关键指标" class="mb-6" />
        <DashboardMetricsPanel />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
definePageMeta({
  layout: "portal",
  middleware: "auth",
});

const coreApps = [
  {
    name: "档案管理",
    description: "全生命周期管理：涵盖收集、整理、归档与存储。",
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
    iconBg: "bg-secondary/10",
    iconColor: "text-secondary",
    hoverColor: "group-hover:text-indigo-600",
    href: "/data-center",
  },
  {
    name: "数据保全中心",
    description: "四性检测，长期保存策略，保障数据安全可读。",
    icon: "heroicons:shield-check",
    iconBg: "bg-success/10",
    iconColor: "text-success",
    hoverColor: "group-hover:text-emerald-600",
    href: "/preservation",
  },
  {
    name: "平台基础管理",
    description: "IAM身份认证、RBAC权限配置及系统参数设置。",
    icon: "heroicons:cog-8-tooth",
    iconBg: "bg-base-300",
    iconColor: "text-base-content/70",
    hoverColor: "group-hover:text-slate-600",
    href: "/admin",
  },
  {
    name: "利用服务中心",
    description: "面向公众的查档服务，检索门户与利用借阅。",
    icon: "heroicons:user-group",
    iconBg: "bg-warning/10",
    iconColor: "text-warning",
    hoverColor: "group-hover:text-orange-600",
    href: "/service",
  },
  {
    name: "系统审计中心",
    description: "操作日志记录，安全监控告警与统计报表。",
    icon: "heroicons:clipboard-document-check",
    iconBg: "bg-error/10",
    iconColor: "text-error",
    hoverColor: "group-hover:text-rose-600",
    href: "/audit",
  },
];
</script>
