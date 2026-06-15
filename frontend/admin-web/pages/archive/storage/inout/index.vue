<template>
  <div class="flex flex-col gap-3 min-h-0 flex-1">
    <AdminPageHeader
      title="出入库记录"
      description="档案出入库登记（借阅 / 修复 / 数字化 / 移库 / 盘点）；借阅出库由利用模块自动生成"
      icon="heroicons:arrows-right-left"
    />

    <!-- 筛选 + 工具 -->
    <div class="pro-card p-4 flex flex-wrap items-center gap-3">
      <NInput v-model:value="filter.keyword" placeholder="档号 / 题名 / 单号" clearable style="width: 240px" @keydown.enter="reload">
        <template #prefix><Icon name="heroicons:magnifying-glass" class="w-4 h-4 text-gray-400" /></template>
      </NInput>
      <NSelect v-model:value="filter.direction" :options="directionOptions" placeholder="出/入库" clearable style="width: 120px" @update:value="reload" />
      <NSelect v-model:value="filter.biz_type" :options="bizOptions" placeholder="业务类型" clearable style="width: 140px" @update:value="reload" />
      <NSelect v-model:value="filter.status" :options="statusOptions" placeholder="状态" clearable style="width: 120px" @update:value="reload" />
      <NButton tertiary @click="reload">查询</NButton>
      <div class="flex-1" />
      <span class="text-sm text-gray-500">共 {{ total }} 条</span>
      <NButton type="primary" @click="openCreate">
        <template #icon><Icon name="heroicons:plus" class="w-4 h-4" /></template>
        出入库登记
      </NButton>
    </div>

    <div class="pro-card p-4 flex-1 min-h-0 flex flex-col gap-3">
      <ProTable :columns="columns" :data="records" :loading="loading" :page-size="0" size="small" />
      <div class="flex justify-end">
        <NPagination v-model:page="page" :page-size="PAGE_SIZE" :item-count="total" size="small" @update:page="load" />
      </div>
    </div>

    <!-- 登记表单 -->
    <NModal v-model:show="showCreate" preset="card" title="出入库登记" style="width: 560px; max-width: 95vw">
      <div class="grid grid-cols-2 gap-4">
        <Field label="方向" required>
          <NSelect v-model:value="form.direction" :options="directionOptions" />
        </Field>
        <Field label="业务类型" required>
          <NSelect v-model:value="form.biz_type" :options="bizOptions" />
        </Field>
        <Field label="档号"><NInput v-model:value="form.DH" placeholder="档号" /></Field>
        <Field label="题名"><NInput v-model:value="form.TM" placeholder="题名" /></Field>
        <Field label="库房">
          <NSelect v-model:value="form.vault_id" :options="vaultOptions" placeholder="选择库房" clearable />
        </Field>
        <Field label="数量"><NInputNumber v-model:value="form.qty" :min="1" class="w-full" /></Field>
        <Field label="经办 / 借出对象"><NInput v-model:value="form.counterparty" placeholder="对方单位 / 个人" /></Field>
        <Field v-if="form.direction === 'out'" label="应还日期">
          <NInput v-model:value="form.expected_return" placeholder="YYYY-MM-DD" />
        </Field>
        <div class="col-span-2">
          <Field label="备注"><NInput v-model:value="form.notes" type="textarea" :rows="2" /></Field>
        </div>
      </div>
      <template #footer>
        <div class="flex justify-end gap-3">
          <NButton @click="showCreate = false">取消</NButton>
          <NButton type="primary" :loading="saving" @click="submit">登记</NButton>
        </div>
      </template>
    </NModal>
  </div>
</template>

<script setup lang="tsx">
import { h, onMounted, reactive, ref } from "vue";
import { NButton, NInput, NInputNumber, NModal, NPagination, NSelect, NTag, useMessage } from "naive-ui";
import type { DataTableColumns } from "naive-ui";
import { AdminPageHeader } from "@/components/admin";
import { ProTable } from "@/components/ui";
import { StorageAPI } from "@/api/storage";
import type { InoutBizType, InoutDirection, InoutRecord, InoutStatus, Vault } from "@/api/storage";

definePageMeta({ layout: "archive", middleware: "auth" });

const message = useMessage();
const PAGE_SIZE = 20;

type SlotsCtx = { slots: { default?: () => unknown } };
const Field = (props: { label: string; required?: boolean }, { slots }: SlotsCtx) =>
  h("div", { class: "flex flex-col gap-1" }, [
    h("span", { class: "text-[12px]", style: "color:var(--semi-color-text-3)" }, [
      props.label,
      props.required ? h("span", { class: "text-red-500 ml-0.5" }, "*") : null,
    ]),
    slots.default?.(),
  ]);

const directionOptions = [{ label: "出库", value: "out" }, { label: "入库", value: "in" }];
const bizOptions = [
  { label: "借阅", value: "borrow" }, { label: "修复", value: "repair" },
  { label: "数字化", value: "digitize" }, { label: "移库", value: "relocate" },
  { label: "盘点", value: "inventory" }, { label: "其他", value: "other" },
];
const statusOptions = [
  { label: "在外", value: "out" }, { label: "已归还", value: "returned" }, { label: "已完成", value: "done" },
];
const BIZ_LABEL: Record<string, string> = {
  borrow: "借阅", repair: "修复", digitize: "数字化", relocate: "移库", inventory: "盘点", other: "其他",
};
const STATUS_META: Record<string, { label: string; type: "warning" | "success" | "default" }> = {
  out: { label: "在外", type: "warning" }, returned: { label: "已归还", type: "success" }, done: { label: "已完成", type: "default" },
};

const records = ref<InoutRecord[]>([]);
const total = ref(0);
const page = ref(1);
const loading = ref(false);
const filter = reactive({
  keyword: "",
  direction: null as InoutDirection | null,
  biz_type: null as InoutBizType | null,
  status: null as InoutStatus | null,
});
const vaultOptions = ref<{ label: string; value: string }[]>([]);

async function load() {
  loading.value = true;
  try {
    const res = await StorageAPI.listInout({
      keyword: filter.keyword || undefined,
      direction: filter.direction ?? undefined,
      biz_type: filter.biz_type ?? undefined,
      status: filter.status ?? undefined,
      skip: (page.value - 1) * PAGE_SIZE,
      limit: PAGE_SIZE,
    });
    if (res.code === 0) {
      records.value = res.data.items;
      total.value = res.data.total;
    }
  } finally {
    loading.value = false;
  }
}

function reload() {
  page.value = 1;
  load();
}

const columns: DataTableColumns<InoutRecord> = [
  { title: "单号", key: "record_no", width: 130 },
  {
    title: "方向", key: "direction", width: 70,
    render: (r) => h(NTag, { size: "small", type: r.direction === "out" ? "warning" : "info", bordered: false },
      { default: () => (r.direction === "out" ? "出库" : "入库") }),
  },
  { title: "业务", key: "biz_type", width: 80, render: (r) => BIZ_LABEL[r.biz_type] ?? r.biz_type },
  { title: "档号", key: "DH", width: 170, ellipsis: { tooltip: true }, render: (r) => r.DH || "—" },
  { title: "题名", key: "TM", minWidth: 180, ellipsis: { tooltip: true }, render: (r) => r.TM || "—" },
  { title: "经办对象", key: "counterparty", width: 120, render: (r) => r.counterparty || "—" },
  {
    title: "状态", key: "status", width: 90,
    render: (r) => {
      const m = STATUS_META[r.status] ?? { label: r.status, type: "default" as const };
      return h(NTag, { size: "small", type: m.type, round: true, bordered: false }, { default: () => m.label });
    },
  },
  {
    title: "出/入时间", key: "out_time", width: 150,
    render: (r) => (r.direction === "out" ? r.out_time : r.in_time)?.slice(0, 16).replace("T", " ") ?? "—",
  },
  {
    title: "操作", key: "actions", width: 90,
    render: (r) => (r.status === "out"
      ? h(NButton, { size: "tiny", tertiary: true, type: "primary", onClick: () => markReturned(r) }, { default: () => "登记归还" })
      : null),
  },
];

async function markReturned(r: InoutRecord) {
  const res = await StorageAPI.returnInout(r.id);
  if (res.code === 0) {
    message.success("已登记归还");
    await load();
  } else {
    message.error(res.message);
  }
}

// ── 登记 ──
const showCreate = ref(false);
const saving = ref(false);
const form = reactive({
  direction: "out" as InoutDirection,
  biz_type: "repair" as InoutBizType,
  DH: "", TM: "", vault_id: null as string | null,
  qty: 1, counterparty: "", expected_return: "", notes: "",
});

function openCreate() {
  Object.assign(form, {
    direction: "out", biz_type: "repair", DH: "", TM: "", vault_id: null,
    qty: 1, counterparty: "", expected_return: "", notes: "",
  });
  showCreate.value = true;
}

async function submit() {
  const res = await StorageAPI.createInout({
    direction: form.direction, biz_type: form.biz_type,
    DH: form.DH || undefined, TM: form.TM || undefined,
    vault_id: form.vault_id ?? undefined, qty: form.qty,
    counterparty: form.counterparty || undefined,
    expected_return: form.direction === "out" && form.expected_return ? `${form.expected_return}T00:00:00` : undefined,
    notes: form.notes || undefined,
  });
  if (res.code === 0) {
    message.success("登记成功");
    showCreate.value = false;
    reload();
  } else {
    message.error(res.message);
  }
}

onMounted(async () => {
  load();
  const res = await StorageAPI.listVaults();
  if (res.code === 0) {
    vaultOptions.value = res.data.map((v: Vault) => ({ label: `${v.code} ${v.name}`, value: v.id }));
  }
});
</script>
