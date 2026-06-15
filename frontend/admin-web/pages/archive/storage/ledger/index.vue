<template>
  <div class="flex flex-col gap-4">
    <AdminPageHeader
      title="保管台账"
      description="库房容量占用与出入库总览"
      icon="heroicons:book-open"
    />

    <div class="grid grid-cols-2 md:grid-cols-5 gap-4">
      <KpiCard label="库房数量" :value="String(summary.vault_count)" sub="间" icon="heroicons:building-office-2" icon-bg="rgba(59,130,246,0.1)" icon-color="#3b82f6" />
      <KpiCard label="设计总容量" :value="summary.total_capacity.toLocaleString()" sub="卷/件" icon="heroicons:cube" icon-bg="rgba(16,185,129,0.1)" icon-color="#10b981" />
      <KpiCard label="已用容量" :value="summary.total_used.toLocaleString()" sub="卷/件" icon="heroicons:archive-box" icon-bg="rgba(245,158,11,0.1)" icon-color="#f59e0b" />
      <KpiCard label="整体填充率" :value="`${summary.fill_rate}%`" sub="平均占用" icon="heroicons:chart-pie" icon-bg="rgba(139,92,246,0.1)" icon-color="#8b5cf6" />
      <KpiCard label="在外档案" :value="String(summary.out_active)" sub="件未归还" icon="heroicons:arrow-up-right" icon-bg="rgba(239,68,68,0.1)" icon-color="#ef4444" />
    </div>

    <div class="pro-card p-5">
      <p class="text-[14px] font-semibold mb-3" style="color:var(--semi-color-text-0)">各库房保管明细</p>
      <ProTable :columns="columns" :data="vaults" :loading="loading" :page-size="0" size="small" />
    </div>
  </div>
</template>

<script setup lang="tsx">
import { h, onMounted, reactive, ref } from "vue";
import { NProgress, NTag } from "naive-ui";
import type { DataTableColumns } from "naive-ui";
import { AdminPageHeader, KpiCard } from "@/components/admin";
import { ProTable } from "@/components/ui";
import { StorageAPI } from "@/api/storage";
import type { StorageLedger, Vault } from "@/api/storage";

definePageMeta({ layout: "archive", middleware: "auth" });

const loading = ref(false);
const vaults = ref<Vault[]>([]);
const summary = reactive<StorageLedger["summary"]>({
  vault_count: 0, total_capacity: 0, total_used: 0, fill_rate: 0, out_active: 0, inout_total: 0,
});

function fillColor(p: number): string {
  if (p >= 90) return "#ef4444";
  if (p >= 70) return "#f59e0b";
  return "#10b981";
}

const columns: DataTableColumns<Vault> = [
  { title: "库房", key: "name", minWidth: 180, render: (r) => `${r.code} ${r.name}` },
  { title: "位置", key: "location", width: 150, render: (r) => r.location || "—" },
  { title: "架体", key: "grid", width: 110, render: (r) => `${r.rows}×${r.columns}×${r.layers}` },
  { title: "容量", key: "capacity", width: 130, render: (r) => `${r.used.toLocaleString()} / ${r.capacity.toLocaleString()}` },
  {
    title: "填充率", key: "fill_rate", width: 160,
    render: (r) => h(NProgress, {
      percentage: r.fill_rate, height: 8, color: fillColor(r.fill_rate),
      railColor: "var(--semi-color-fill-1)", style: "width:130px",
    }),
  },
  { title: "温度", key: "temperature", width: 80, render: (r) => `${r.temperature ?? "—"} ℃` },
  { title: "湿度", key: "humidity", width: 90, render: (r) => `${r.humidity ?? "—"} %RH` },
  {
    title: "状态", key: "status", width: 90,
    render: (r) => {
      const m: Record<string, { label: string; type: "success" | "warning" | "default" }> = {
        active: { label: "在用", type: "success" }, maintenance: { label: "维护中", type: "warning" }, disabled: { label: "停用", type: "default" },
      };
      const meta = m[r.status] ?? { label: r.status, type: "default" as const };
      return h(NTag, { size: "small", type: meta.type, round: true, bordered: false }, { default: () => meta.label });
    },
  },
];

async function load() {
  loading.value = true;
  try {
    const res = await StorageAPI.ledger();
    if (res.code === 0) {
      Object.assign(summary, res.data.summary);
      vaults.value = res.data.vaults;
    }
  } finally {
    loading.value = false;
  }
}

onMounted(load);
</script>
