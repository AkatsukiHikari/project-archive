<template>
  <NModal
    :show="show"
    preset="card"
    title="按档号规则批量重编档号"
    style="width: 820px; max-width: 95vw"
    :mask-closable="false"
    @update:show="(v: boolean) => emit('update:show', v)"
  >
    <div class="flex flex-col gap-4">
      <p class="text-[12px]" style="color:var(--semi-color-text-2)">
        按 文件日期 → 题名 排序后从起始序号连续编号，先预览确认再执行。
      </p>

      <!-- 范围选择 -->
      <NRadioGroup v-model:value="scope" @update:value="preview = null">
        <div class="flex flex-col gap-1.5">
          <NRadio value="selected" :disabled="!selectedIds.length">
            勾选的档案（{{ selectedIds.length }} 条）
          </NRadio>
          <NRadio value="query" :disabled="!queryTotal">
            当前查询条件命中的全部档案（{{ queryTotal }} 条，跨页全量应用）
          </NRadio>
        </div>
      </NRadioGroup>

      <div class="flex items-end gap-4">
        <div class="flex flex-col gap-1 flex-1">
          <span class="text-sm font-medium">档号规则 <span class="text-red-500">*</span></span>
          <NSelect v-model:value="ruleId" :options="ruleOptions" placeholder="选择启用的档号规则" />
        </div>
        <div class="flex flex-col gap-1 w-36">
          <span class="text-sm font-medium">起始序号</span>
          <NInputNumber v-model:value="startSeq" :min="1" class="w-full" />
        </div>
        <NButton type="primary" secondary :disabled="!ruleId" :loading="previewing" @click="loadPreview">
          <template #icon><Icon name="heroicons:eye" class="w-4 h-4" /></template>
          预览
        </NButton>
      </div>

      <template v-if="preview">
        <div class="flex items-center gap-4 text-[12px]">
          <span>共 {{ preview.total }} 条</span>
          <span v-if="preview.conflicts" style="color:oklch(var(--er))">
            {{ preview.conflicts }} 条与现有档号冲突，需先处理才能执行
          </span>
          <span v-else style="color:oklch(var(--su))">无冲突，可以执行</span>
        </div>
        <ProTable :columns="columns" :data="preview.rows" :page-size="0" size="small" max-height="340" />
      </template>
    </div>

    <template #footer>
      <div class="flex justify-end gap-3">
        <NButton @click="emit('update:show', false)">取消</NButton>
        <NButton
          type="primary"
          :disabled="!preview || preview.conflicts > 0"
          :loading="applying"
          @click="apply"
        >
          执行重编（{{ preview?.total ?? 0 }} 条）
        </NButton>
      </div>
    </template>
  </NModal>
</template>

<script setup lang="tsx">
import { computed, h, onMounted, ref, watch } from "vue";
import { NButton, NInputNumber, NModal, NRadio, NRadioGroup, NSelect, NTag, useMessage } from "naive-ui";
import type { DataTableColumns } from "naive-ui";
import { ProTable } from "@/components/ui";
import { NoRuleAPI, OrganizeAPI } from "@/api/repository";
import type { ArchiveListParams, NoRule, RenumberPreviewResult, RenumberRow } from "@/api/repository";

const props = defineProps<{
  show: boolean;
  selectedIds: string[];
  /** 当前列表查询条件（按查询全量应用时使用） */
  query?: Partial<ArchiveListParams>;
  queryTotal?: number;
}>();
const emit = defineEmits<{ "update:show": [boolean]; done: [] }>();

const message = useMessage();
const rules = ref<NoRule[]>([]);
const ruleId = ref<string | null>(null);
const startSeq = ref(1);
const preview = ref<RenumberPreviewResult | null>(null);
const previewing = ref(false);
const applying = ref(false);

const ruleOptions = computed(() =>
  rules.value.filter((r) => r.is_active).map((r) => ({ label: r.name, value: r.id })),
);

const scope = ref<"selected" | "query">("selected");

watch(() => props.show, (v) => {
  if (v) {
    preview.value = null;
    startSeq.value = 1;
    scope.value = props.selectedIds.length ? "selected" : "query";
  }
});

function payload() {
  if (scope.value === "selected") {
    return { rule_id: ruleId.value!, ids: props.selectedIds, start_seq: startSeq.value };
  }
  return { rule_id: ruleId.value!, query: props.query ?? {}, start_seq: startSeq.value };
}

async function loadPreview() {
  if (scope.value === "selected" && !props.selectedIds.length) {
    return message.warning("请先在列表勾选档案");
  }
  if (scope.value === "query" && !props.queryTotal) {
    return message.warning("当前查询没有命中档案");
  }
  previewing.value = true;
  try {
    const res = await OrganizeAPI.renumberPreview(payload());
    if (res.code === 0) preview.value = res.data;
    else message.error(res.message);
  } finally {
    previewing.value = false;
  }
}

async function apply() {
  applying.value = true;
  try {
    const res = await OrganizeAPI.renumberApply(payload());
    if (res.code === 0) {
      message.success(`已重编 ${res.data.renumbered} 条档号`);
      emit("update:show", false);
      emit("done");
    } else {
      message.error(res.message);
    }
  } finally {
    applying.value = false;
  }
}

const columns: DataTableColumns<RenumberRow> = [
  { title: "题名", key: "TM", minWidth: 200, ellipsis: { tooltip: true } },
  { title: "文件日期", key: "WJRQ", width: 100, render: (r) => r.WJRQ ?? "—" },
  {
    title: "原档号", key: "DH_old", width: 190,
    render: (r) => h("code", { class: "font-mono text-[11.5px]" }, r.DH_old ?? "（空）"),
  },
  {
    title: "新档号", key: "DH_new", width: 190,
    render: (r) => h("code", { class: "font-mono text-[11.5px]", style: "color:oklch(var(--p))" }, r.DH_new),
  },
  {
    title: "", key: "conflict", width: 70,
    render: (r) => (r.conflict
      ? h(NTag, { size: "tiny", type: "error", bordered: false }, { default: () => "冲突" })
      : null),
  },
];

onMounted(async () => {
  const res = await NoRuleAPI.list();
  rules.value = res.data ?? [];
  const active = rules.value.find((r) => r.is_active);
  if (active) ruleId.value = active.id;
});
</script>
