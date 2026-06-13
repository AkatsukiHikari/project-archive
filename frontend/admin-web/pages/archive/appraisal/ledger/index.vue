<template>
  <div class="flex flex-col gap-4">
    <AdminPageHeader
      title="鉴定台账"
      description="历次开放鉴定的全部结论记录，按全宗 / 结论 / 关键词检索"
      icon="heroicons:book-open"
    />

    <div class="pro-card p-4 flex flex-wrap items-center gap-3">
      <NInput
        v-model:value="filterQzh"
        placeholder="全宗号"
        clearable
        style="width: 130px"
        @keyup.enter="reload"
        @clear="reload"
      />
      <NSelect
        v-model:value="filterKfzt"
        :options="kfztOptions"
        placeholder="开放状态"
        clearable
        style="width: 140px"
        @update:value="reload"
      />
      <NInput
        v-model:value="filterKeyword"
        placeholder="题名 / 档号"
        clearable
        style="width: 200px"
        @keyup.enter="reload"
        @clear="reload"
      />
      <NButton tertiary @click="reload">
        <template #icon><Icon name="heroicons:arrow-path" class="w-4 h-4" /></template>
        刷新
      </NButton>
      <div class="flex-1" />
      <span class="text-sm text-gray-400">共 {{ total }} 条鉴定记录</span>
    </div>

    <div class="pro-card p-5">
      <ProTable :columns="columns" :data="entries" :loading="loading" :page-size="0" size="small" />
      <div class="flex justify-end mt-3">
        <NPagination
          v-model:page="page"
          :page-size="PAGE_SIZE"
          :item-count="total"
          size="small"
          @update:page="load"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="tsx">
import { h, onMounted, ref } from "vue";
import { NButton, NInput, NPagination, NSelect, NTooltip } from "naive-ui";
import type { DataTableColumns } from "naive-ui";
import { AdminPageHeader } from "@/components/admin";
import { ProTable } from "@/components/ui";
import { KfztTag } from "@/components/archive";
import { AppraisalAPI } from "@/api/appraisal";
import type { AppraisalItem, Kfzt } from "@/api/appraisal";

definePageMeta({ layout: "archive", middleware: "auth" });

const PAGE_SIZE = 20;
const kfztOptions = (["开放", "控制使用", "延期开放", "不开放"] as Kfzt[]).map((v) => ({ label: v, value: v }));

const loading = ref(false);
const entries = ref<AppraisalItem[]>([]);
const total = ref(0);
const page = ref(1);
const filterQzh = ref("");
const filterKfzt = ref<Kfzt | null>(null);
const filterKeyword = ref("");

async function load() {
  loading.value = true;
  try {
    const res = await AppraisalAPI.listLedger({
      qzh: filterQzh.value || undefined,
      kfzt: filterKfzt.value ?? undefined,
      keyword: filterKeyword.value || undefined,
      skip: (page.value - 1) * PAGE_SIZE,
      limit: PAGE_SIZE,
    });
    entries.value = res.data.items;
    total.value = res.data.total;
  } finally {
    loading.value = false;
  }
}

function reload() {
  page.value = 1;
  load();
}

const columns: DataTableColumns<AppraisalItem> = [
  { title: "档号", key: "DH", width: 190, ellipsis: { tooltip: true } },
  { title: "题名", key: "TM", minWidth: 200, ellipsis: { tooltip: true } },
  { title: "全宗", key: "QZH", width: 80 },
  { title: "年度", key: "ND", width: 60 },
  { title: "保管期限", key: "BGQX", width: 85 },
  { title: "结论", key: "final_kfzt", width: 100, render: (r) => h(KfztTag, { value: r.final_kfzt }) },
  {
    title: "结论理由", key: "final_reason", minWidth: 220,
    render: (r) => h(NTooltip, null, {
      trigger: () => h("span", { class: "text-xs text-gray-600 line-clamp-1" }, r.final_reason ?? "—"),
      default: () => r.final_reason ?? "—",
    }),
  },
  { title: "所属计划", key: "plan_name", width: 170, ellipsis: { tooltip: true }, render: (r) => `${r.plan_name ?? ""}` },
  { title: "审核时间", key: "reviewed_at", width: 105, render: (r) => r.reviewed_at?.slice(0, 10) ?? "—" },
];

onMounted(load);
</script>
