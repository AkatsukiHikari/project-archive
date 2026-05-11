<template>
  <div class="flex flex-col gap-4">
    <AdminPageHeader
      title="档号规则"
      description="配置档案编号自动生成规则，支持字段、序号、日期多段组合"
      icon="heroicons:hashtag"
    />

    <ProTable :columns="columns" :data="ruleList" :loading="loading" empty-content="暂无档号规则">
      <template #toolbar-right>
        <NButton type="primary" @click="openModal(null)">
          <template #icon><Icon name="heroicons:plus" class="w-4 h-4" /></template>
          新增规则
        </NButton>
      </template>
    </ProTable>

    <CrudModal
      v-model:visible="modalVisible"
      :title="isEdit ? '编辑档号规则' : '新增档号规则'"
      :loading="saving"
      :width="800"
      @confirm="submitForm"
    >
      <!-- 基本信息 -->
      <NForm ref="formRef" :model="formData" :rules="formRules" label-placement="left" :label-width="80">
        <div class="grid grid-cols-2 gap-x-4">
          <NFormItem path="name" label="规则名称">
            <NInput v-model:value="formData.name" placeholder="如：文书档案档号" />
          </NFormItem>
          <NFormItem path="category_id" label="所属门类">
            <NSelect v-model:value="formData.category_id" :options="categoryOptions" placeholder="选择门类" />
          </NFormItem>
          <NFormItem path="separator" label="分隔符">
            <NInput v-model:value="formData.separator" placeholder="-" :maxlength="5" class="w-20" />
          </NFormItem>
          <NFormItem path="seq_scope" label="序号范围">
            <NSelect v-model:value="formData.seq_scope" :options="seqScopeOptions" />
          </NFormItem>
          <NFormItem label="启用状态">
            <NSwitch v-model:value="formData.is_active" />
          </NFormItem>
        </div>
      </NForm>

      <!-- 规则段构建器 -->
      <div class="mt-1">
        <div class="flex items-center gap-2 mb-2.5">
          <span class="text-sm font-medium text-base-content/80">规则段</span>
          <span class="text-xs text-base-content/40">从左到右依次拼接，用分隔符连接</span>
          <div class="ml-auto flex items-center gap-1.5">
            <NButton size="tiny" secondary @click="addSegment('field')">
              <template #icon><Icon name="heroicons:tag" class="w-3 h-3" /></template>
              字段
            </NButton>
            <NButton size="tiny" secondary @click="addSegment('literal')">
              <template #icon><Icon name="heroicons:pencil-square" class="w-3 h-3" /></template>
              固定文字
            </NButton>
            <NButton size="tiny" type="success" secondary @click="addSegment('sequence')">
              <template #icon><Icon name="heroicons:hashtag" class="w-3 h-3" /></template>
              序号
            </NButton>
            <NButton size="tiny" type="warning" secondary @click="addSegment('date_part')">
              <template #icon><Icon name="heroicons:calendar-days" class="w-3 h-3" /></template>
              日期
            </NButton>
          </div>
        </div>

        <!-- 空状态 -->
        <div
          v-if="formData.segments.length === 0"
          class="text-sm text-base-content/40 text-center py-8 rounded-lg border border-dashed border-base-content/15"
        >
          点击上方按钮添加规则段
        </div>

        <!-- 段列表 -->
        <div v-else class="flex flex-col gap-1">
          <template v-for="(seg, idx) in formData.segments" :key="idx">
            <div
              class="flex items-center gap-3 px-3 py-2 rounded-lg border"
              :class="segCardClass(seg.type)"
            >
              <!-- 类型标签 -->
              <span class="shrink-0 text-xs font-semibold px-2 py-0.5 rounded-md" :class="segBadgeClass(seg.type)">
                {{ segLabel(seg.type) }}
              </span>

              <!-- 配置区 -->
              <div class="flex-1 flex items-center gap-2 min-w-0 flex-wrap">
                <template v-if="seg.type === 'field'">
                  <span class="text-xs text-base-content/50 shrink-0">取字段：</span>
                  <NSelect
                    :value="seg.field"
                    :options="fieldOptions"
                    size="small"
                    style="width:160px"
                    @update:value="(v) => updateSegment(idx, 'field', v)"
                  />
                </template>

                <template v-else-if="seg.type === 'literal'">
                  <span class="text-xs text-base-content/50 shrink-0">固定值：</span>
                  <NInput
                    :value="seg.value ?? ''"
                    size="small"
                    placeholder="如：WS、永久"
                    style="width:140px"
                    @update:value="(v) => updateSegment(idx, 'value', v)"
                  />
                </template>

                <template v-else-if="seg.type === 'sequence'">
                  <span class="text-xs text-base-content/50 shrink-0">补零：</span>
                  <NInputNumber
                    :value="seg.padding ?? 4"
                    size="small"
                    :min="1"
                    :max="10"
                    style="width:72px"
                    @update:value="(v) => updateSegment(idx, 'padding', v ?? 4)"
                  />
                  <span class="text-xs text-base-content/50 shrink-0">位 &nbsp;|&nbsp; 重置范围：</span>
                  <NSelect
                    :value="seg.scope ?? formData.seq_scope"
                    :options="seqScopeOptions"
                    size="small"
                    style="width:130px"
                    @update:value="(v) => updateSegment(idx, 'scope', v)"
                  />
                </template>

                <template v-else-if="seg.type === 'date_part'">
                  <span class="text-xs text-base-content/50 shrink-0">格式：</span>
                  <NInput
                    :value="seg.date_format ?? '%Y'"
                    size="small"
                    placeholder="%Y"
                    style="width:110px"
                    @update:value="(v) => updateSegment(idx, 'date_format', v)"
                  />
                  <span class="text-xs text-base-content/30 shrink-0">（%Y年 %m月 %d日）</span>
                </template>
              </div>

              <!-- 排序 / 删除 -->
              <div class="shrink-0 flex items-center">
                <NButton text size="tiny" :disabled="idx === 0" @click="moveUp(idx)">
                  <Icon name="heroicons:chevron-up" class="w-4 h-4" />
                </NButton>
                <NButton text size="tiny" :disabled="idx === formData.segments.length - 1" @click="moveDown(idx)">
                  <Icon name="heroicons:chevron-down" class="w-4 h-4" />
                </NButton>
                <NButton text size="tiny" class="!text-error/60 hover:!text-error" @click="removeSegment(idx)">
                  <Icon name="heroicons:x-mark" class="w-4 h-4" />
                </NButton>
              </div>
            </div>

            <!-- 段间分隔符示意 -->
            <div v-if="idx < formData.segments.length - 1" class="flex justify-center py-0.5">
              <span class="text-xs text-base-content/25 font-mono">{{ formData.separator || '-' }}</span>
            </div>
          </template>
        </div>
      </div>

      <!-- 档号预览 -->
      <div class="mt-4 rounded-lg border border-base-content/10 bg-base-200/30 p-4">
        <p class="text-sm font-medium text-base-content/80 mb-3">
          档号预览
          <span class="text-xs text-base-content/40 font-normal ml-2">序号段显示占位符，不计入实际序列</span>
        </p>
        <div class="grid grid-cols-2 gap-x-4 gap-y-2 mb-3">
          <label class="flex items-center gap-2 text-xs">
            <span class="w-14 shrink-0 text-base-content/50">全宗号</span>
            <NInput v-model:value="sample.QZH" size="small" placeholder="J001" />
          </label>
          <label class="flex items-center gap-2 text-xs">
            <span class="w-14 shrink-0 text-base-content/50">年度</span>
            <NInput v-model:value="sample.ND" size="small" placeholder="2024" />
          </label>
          <label class="flex items-center gap-2 text-xs">
            <span class="w-14 shrink-0 text-base-content/50">责任者</span>
            <NInput v-model:value="sample.RZZ" size="small" placeholder="可选" />
          </label>
          <label class="flex items-center gap-2 text-xs">
            <span class="w-14 shrink-0 text-base-content/50">文件日期</span>
            <NInput v-model:value="sample.WJRQ" size="small" placeholder="2024-01-01" />
          </label>
        </div>
        <div class="flex items-center gap-3 flex-wrap">
          <NButton size="small" :disabled="formData.segments.length === 0" @click="buildPreview">
            生成预览
          </NButton>
          <div v-if="previewParts.length > 0" class="flex items-center gap-1 flex-wrap">
            <template v-for="(part, i) in previewParts" :key="i">
              <span v-if="i > 0" class="text-xs text-base-content/30 font-mono">
                {{ formData.separator || '-' }}
              </span>
              <span
                class="text-xs font-mono px-1.5 py-0.5 rounded"
                :class="segBadgeClass(formData.segments[i]?.type ?? 'literal')"
              >{{ part || '—' }}</span>
            </template>
            <span class="text-sm font-mono font-semibold ml-3 text-base-content">
              → {{ previewNo }}
            </span>
          </div>
        </div>
      </div>
    </CrudModal>
  </div>
</template>

<script setup lang="tsx">
import { ref, computed, reactive, onMounted } from "vue";
import {
  NButton, NSelect, NInput, NInputNumber, NForm, NFormItem, NSwitch, NTag,
  useMessage, useDialog,
} from "naive-ui";
import type { FormInst } from "naive-ui";
import {
  CategoryAPI, type ArchiveCategory,
  NoRuleAPI, type NoRule, type NoRuleCreate, type NoRuleUpdate,
  type SegmentDef, type SegmentType, type SeqScope, type RuleTemplate,
} from "@/api/repository";
import { AdminPageHeader } from "@/components/admin";
import { ProTable, CrudModal } from "@/components/ui";

definePageMeta({ layout: "archive", middleware: "auth" });

// ── 全局状态 ────────────────────────────────────────────────────────────────
const message = useMessage();
const dialog = useDialog();
const ruleList = ref<NoRule[]>([]);
const categories = ref<ArchiveCategory[]>([]);
const loading = ref(false);

// ── 选项配置 ────────────────────────────────────────────────────────────────
const categoryOptions = computed(() =>
  categories.value.map((c) => ({ label: `${c.code} - ${c.name}`, value: c.id })),
);

const seqScopeOptions = [
  { label: "目录", value: "catalog" },
  { label: "目录 + 年度", value: "catalog_year" },
  { label: "全宗", value: "fonds" },
];

const fieldOptions = [
  { label: "全宗号 (QZH)", value: "QZH" },
  { label: "年度 (ND)", value: "ND" },
  { label: "责任者 (RZZ)", value: "RZZ" },
];

const seqScopeLabel: Record<string, string> = {
  catalog: "目录",
  catalog_year: "目录+年度",
  fonds: "全宗",
};

// ── ProTable 列定义 ──────────────────────────────────────────────────────────
const columns = [
  {
    title: "规则名称", key: "name",
    search: { placeholder: "请输入规则名称" },
  },
  {
    title: "所属门类", key: "category_id",
    render: (row: NoRule) => {
      const cat = categories.value.find((c) => c.id === row.category_id);
      return cat
        ? <NTag size="small">{cat.code} - {cat.name}</NTag>
        : <span class="text-base-content/30">—</span>;
    },
  },
  {
    title: "规则段", key: "segments",
    render: (row: NoRule) => {
      const segs = row.rule_template?.segments ?? [];
      if (segs.length === 0) return <span class="text-base-content/30">未配置</span>;
      const sep = row.rule_template?.separator ?? "-";
      return (
        <div class="flex items-center gap-1 flex-wrap">
          {segs.map((s, i) => (
            <>
              {i > 0 && <span class="text-base-content/30 text-xs font-mono">{sep}</span>}
              <span class={`text-xs px-1.5 py-0.5 rounded font-mono ${segBadgeClass(s.type)}`}>
                {segPreviewLabel(s)}
              </span>
            </>
          ))}
        </div>
      );
    },
  },
  {
    title: "序号范围", key: "seq_scope",
    search: { type: "select" as const, options: seqScopeOptions },
    render: (row: NoRule) => seqScopeLabel[row.seq_scope] ?? row.seq_scope,
  },
  {
    title: "启用", key: "is_active",
    render: (row: NoRule) => (
      <NSwitch
        value={row.is_active}
        size="small"
        onUpdateValue={(v: boolean) => toggleActive(row, v)}
      />
    ),
  },
  {
    title: "操作", key: "actions", width: 120,
    render: (row: NoRule) => (
      <div class="flex items-center gap-1">
        <NButton size="small" onClick={() => openModal(row)}>编辑</NButton>
        <NButton size="small" type="error" onClick={() => confirmDelete(row)}>删除</NButton>
      </div>
    ),
  },
];

// ── 弹窗状态 ────────────────────────────────────────────────────────────────
const modalVisible = ref(false);
const saving = ref(false);
const isEdit = ref(false);
const editId = ref<string | null>(null);
const formRef = ref<FormInst | null>(null);

const emptyForm = () => ({
  name: "",
  category_id: null as string | null,
  separator: "-",
  seq_scope: "catalog_year" as SeqScope,
  is_active: true,
  segments: [] as SegmentDef[],
});

const formData = reactive(emptyForm());

const formRules = {
  name: [{ required: true, message: "请输入规则名称", trigger: "blur" }],
  category_id: [{ required: true, message: "请选择所属门类", trigger: "change" }],
};

// ── 预览状态 ────────────────────────────────────────────────────────────────
const sample = reactive({
  QZH: "J001",
  ND: "2024",
  RZZ: "",
  WJRQ: "2024-01-01",
});

const previewParts = ref<string[]>([]);
const previewNo = ref("");

// ── 段样式 ──────────────────────────────────────────────────────────────────
const segConfig: Record<SegmentType, { label: string; card: string; badge: string }> = {
  field:     { label: "字段", card: "border-primary/25 bg-primary/5",        badge: "bg-primary/10 text-primary" },
  literal:   { label: "固定", card: "border-base-content/15 bg-base-200/60", badge: "bg-base-content/10 text-base-content/60" },
  sequence:  { label: "序号", card: "border-success/25 bg-success/5",        badge: "bg-success/10 text-success" },
  date_part: { label: "日期", card: "border-warning/25 bg-warning/5",        badge: "bg-warning/10 text-warning" },
};

function segCardClass(type: SegmentType) { return segConfig[type].card; }
function segBadgeClass(type: SegmentType) { return segConfig[type].badge; }
function segLabel(type: SegmentType) { return segConfig[type].label; }

function segPreviewLabel(seg: SegmentDef): string {
  if (seg.type === "field") return seg.field ?? "?";
  if (seg.type === "literal") return `"${seg.value ?? ""}"`;
  if (seg.type === "sequence") return `${"0".repeat(seg.padding ?? 4)}`;
  if (seg.type === "date_part") return seg.date_format ?? "%Y";
  return "";
}

// ── 段操作 ──────────────────────────────────────────────────────────────────
function createSegment(type: SegmentType): SegmentDef {
  if (type === "field")     return { type, field: "QZH" };
  if (type === "literal")   return { type, value: "" };
  if (type === "sequence")  return { type, padding: 4, scope: formData.seq_scope };
  if (type === "date_part") return { type, date_field: "WJRQ", date_format: "%Y" };
  return { type };
}

function addSegment(type: SegmentType) {
  formData.segments = [...formData.segments, createSegment(type)];
}

function removeSegment(idx: number) {
  formData.segments = formData.segments.filter((_, i) => i !== idx);
}

function moveUp(idx: number) {
  if (idx === 0) return;
  const arr = [...formData.segments];
  [arr[idx - 1], arr[idx]] = [arr[idx], arr[idx - 1]];
  formData.segments = arr;
}

function moveDown(idx: number) {
  if (idx === formData.segments.length - 1) return;
  const arr = [...formData.segments];
  [arr[idx], arr[idx + 1]] = [arr[idx + 1], arr[idx]];
  formData.segments = arr;
}

function updateSegment(idx: number, key: string, value: unknown) {
  formData.segments = formData.segments.map((seg, i) =>
    i === idx ? { ...seg, [key]: value } : seg,
  );
}

// ── 预览生成 ────────────────────────────────────────────────────────────────
function formatDatePart(dateStr: string, fmt: string): string {
  if (!dateStr) return "";
  const d = new Date(dateStr);
  if (isNaN(d.getTime())) return dateStr.slice(0, 4);
  return fmt
    .replace("%Y", String(d.getFullYear()))
    .replace("%m", String(d.getMonth() + 1).padStart(2, "0"))
    .replace("%d", String(d.getDate()).padStart(2, "0"));
}

function buildPreview() {
  const sampleMap: Record<string, string> = {
    QZH:  sample.QZH,
    ND:   sample.ND,
    RZZ:  sample.RZZ,
    WJRQ: sample.WJRQ,
  };

  const parts = formData.segments.map((seg) => {
    if (seg.type === "field")     return sampleMap[seg.field ?? ""] ?? "";
    if (seg.type === "literal")   return seg.value ?? "";
    if (seg.type === "sequence")  return "0".repeat(seg.padding ?? 4);
    if (seg.type === "date_part") return formatDatePart(
      sampleMap[seg.date_field ?? "WJRQ"] ?? "",
      seg.date_format ?? "%Y",
    );
    return "";
  });

  previewParts.value = parts;
  previewNo.value = parts.join(formData.separator || "-");
}

// ── CRUD ────────────────────────────────────────────────────────────────────
function openModal(row: NoRule | null) {
  previewParts.value = [];
  previewNo.value = "";

  if (row) {
    isEdit.value = true;
    editId.value = row.id;
    const tpl = row.rule_template ?? { separator: "-", segments: [] };
    Object.assign(formData, {
      name:        row.name,
      category_id: row.category_id,
      separator:   tpl.separator ?? "-",
      seq_scope:   row.seq_scope,
      is_active:   row.is_active,
      segments:    tpl.segments ? [...tpl.segments] : [],
    });
  } else {
    isEdit.value = false;
    editId.value = null;
    Object.assign(formData, emptyForm());
  }

  modalVisible.value = true;
}

async function submitForm() {
  try {
    await formRef.value?.validate();
  } catch {
    return;
  }
  if (formData.segments.length === 0) {
    message.warning("请至少添加一个规则段");
    return;
  }

  const tpl: RuleTemplate = {
    separator: formData.separator || "-",
    segments: formData.segments,
  };

  saving.value = true;
  try {
    if (isEdit.value && editId.value) {
      const payload: NoRuleUpdate = {
        name: formData.name,
        rule_template: tpl,
        seq_scope: formData.seq_scope,
        is_active: formData.is_active,
      };
      await NoRuleAPI.update(editId.value, payload);
      message.success("已更新");
    } else {
      const payload: NoRuleCreate = {
        category_id: formData.category_id!,
        name: formData.name,
        rule_template: tpl,
        seq_scope: formData.seq_scope,
        is_active: formData.is_active,
      };
      await NoRuleAPI.create(payload);
      message.success("已创建");
    }
    modalVisible.value = false;
    await loadList();
  } catch {
    // axios 拦截器统一处理错误提示
  } finally {
    saving.value = false;
  }
}

async function toggleActive(row: NoRule, val: boolean) {
  try {
    await NoRuleAPI.update(row.id, { is_active: val });
    ruleList.value = ruleList.value.map((r) =>
      r.id === row.id ? { ...r, is_active: val } : r,
    );
  } catch {
    // revert handled by re-render from original data
  }
}

function confirmDelete(row: NoRule) {
  dialog.warning({
    title: "删除确认",
    content: `确定删除规则「${row.name}」？已配置此规则的门类将无法自动生成档号。`,
    positiveText: "删除",
    negativeText: "取消",
    onPositiveClick: async () => {
      await NoRuleAPI.remove(row.id);
      message.success("已删除");
      await loadList();
    },
  });
}

// ── 数据加载 ────────────────────────────────────────────────────────────────
async function loadList() {
  loading.value = true;
  try {
    const res = await NoRuleAPI.list();
    ruleList.value = res.data;
  } finally {
    loading.value = false;
  }
}

onMounted(async () => {
  const [catRes] = await Promise.all([CategoryAPI.list(), loadList()]);
  categories.value = catRes.data;
});
</script>
