<template>
  <div class="flex flex-col gap-5">

    <!-- 欢迎栏 -->
    <div class="welcome-bar">
      <div>
        <h2 class="welcome-title">{{ greeting }}，{{ displayName }}</h2>
        <p class="welcome-date">{{ todayStr }} · 档案管理系统工作台</p>
      </div>
    </div>

    <!-- KPI 卡片行 -->
    <div class="grid grid-cols-2 lg:grid-cols-4 gap-4">
      <KpiCard
        label="全宗数量"
        value="—"
        sub="个全宗"
        icon="heroicons:building-library"
        icon-bg="rgba(59,130,246,0.1)"
        icon-color="#3b82f6"
      />
      <KpiCard
        label="档案总量"
        value="—"
        sub="条档案"
        icon="heroicons:document-text"
        icon-bg="rgba(245,158,11,0.1)"
        icon-color="#f59e0b"
      />
      <KpiCard
        label="本月新增"
        value="—"
        sub="条档案"
        icon="heroicons:plus-circle"
        icon-bg="rgba(16,185,129,0.1)"
        icon-color="#10b981"
      />
      <KpiCard
        label="待处理"
        value="—"
        sub="项任务"
        icon="heroicons:clock"
        icon-bg="rgba(239,68,68,0.1)"
        icon-color="#ef4444"
      />
    </div>

    <!-- 快捷入口 -->
    <div>
      <p class="section-title mb-3">快捷入口</p>
      <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div
          v-for="sc in shortcuts"
          :key="sc.path"
          class="flex items-center gap-3 p-4 rounded-xl border cursor-pointer transition-all hover:shadow-md"
          style="background: var(--semi-color-bg-0); border-color: var(--semi-color-border)"
          @click="router.push(sc.path)"
        >
          <div
            class="w-10 h-10 rounded-lg flex items-center justify-center shrink-0"
            :style="`background: ${sc.color}22`"
          >
            <Icon :name="sc.icon" class="w-5 h-5" :style="`color: ${sc.color}`" />
          </div>
          <div>
            <p class="text-sm font-medium" style="color: var(--semi-color-text-0)">{{ sc.title }}</p>
            <p class="text-xs mt-0.5" style="color: var(--semi-color-text-3)">{{ sc.desc }}</p>
          </div>
        </div>
      </div>
    </div>

  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { useRouter } from "vue-router";
import { useUserStore } from "@/stores/user";
import KpiCard from "@/components/admin/dashboard/KpiCard.vue";

definePageMeta({ layout: "archive", middleware: "auth" });

const router = useRouter();
const userStore = useUserStore();

const displayName = computed(() =>
  userStore.userInfo?.full_name || userStore.userInfo?.username || "档案员"
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

const shortcuts = [
  { title: "归档移交", desc: "接收部门移交档案",   icon: "heroicons:arrow-down-tray",          color: "#3b82f6", path: "/archive/collection/transfer" },
  { title: "接收登记", desc: "档案接收入库登记",   icon: "heroicons:clipboard-document-check", color: "#10b981", path: "/archive/collection/receive" },
  { title: "档案著录", desc: "新增或编辑档案条目", icon: "heroicons:document-text",            color: "#f59e0b", path: "/archive/organize/records" },
  { title: "利用申请", desc: "处理档案利用申请",   icon: "heroicons:document-plus",            color: "#8b5cf6", path: "/archive/utilization/apply" },
  { title: "查阅登记", desc: "记录来馆查阅信息",   icon: "heroicons:eye",                      color: "#06b6d4", path: "/archive/utilization/reading" },
  { title: "四性检测", desc: "电子档案质量检测",   icon: "heroicons:shield-check",             color: "#ef4444", path: "/archive/storage/detection" },
  { title: "鉴定工作", desc: "开展档案价值鉴定",   icon: "heroicons:clipboard-document-list",  color: "#f97316", path: "/archive/appraisal/evaluate" },
  { title: "批量导入", desc: "CSV/Excel 批量导入", icon: "heroicons:table-cells",              color: "#64748b", path: "/archive/collection/import" },
];
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
.section-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--semi-color-text-0);
}
</style>
