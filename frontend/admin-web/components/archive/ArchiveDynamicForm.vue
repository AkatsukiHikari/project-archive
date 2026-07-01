<template>
  <div v-if="loading" class="py-6 flex justify-center"><NSpin size="small" /></div>
  <div v-else-if="!categoryId" class="py-4 text-center text-[13px]" style="color:var(--semi-color-text-3)">
    请先选择门类，下方将按该门类的著录字段排版渲染
  </div>
  <div v-else-if="renderRows.length === 0" class="py-4 text-center text-[13px]" style="color:var(--semi-color-text-3)">
    该门类暂未定义著录字段
  </div>
  <div v-else class="grid grid-cols-2 gap-x-4 gap-y-2.5">
    <div
      v-for="cell in flatCells"
      :key="cell.def.name"
      :style="{ gridColumn: `span ${cell.span}` }"
    >
      <div class="mb-1 text-[13px]" style="color:var(--semi-color-text-2)">
        {{ cell.def.label }}<span v-if="cell.def.required" style="color:#dc2626"> *</span>
      </div>
      <NSelect
        v-if="cell.def.type === 'select'"
        :value="strOrNull(model[cell.def.name])"
        :options="optionsFor(cell.def)"
        size="small" clearable filterable
        @update:value="(v: string) => set(cell.def.name, v)"
      />
      <NSwitch
        v-else-if="cell.def.type === 'boolean'"
        :value="!!model[cell.def.name]"
        @update:value="(v: boolean) => set(cell.def.name, v)"
      />
      <NInputNumber
        v-else-if="cell.def.type === 'number'"
        :value="numOrNull(model[cell.def.name])"
        size="small" class="w-full"
        @update:value="(v: number | null) => set(cell.def.name, v)"
      />
      <NInput
        v-else-if="cell.def.type === 'textarea'"
        type="textarea"
        :value="strVal(model[cell.def.name])"
        size="small" :autosize="{ minRows: 2, maxRows: 5 }"
        :placeholder="cell.def.placeholder || ''"
        @update:value="(v: string) => set(cell.def.name, v)"
      />
      <NInput
        v-else
        :value="strVal(model[cell.def.name])"
        size="small"
        :placeholder="cell.def.placeholder || (cell.def.type === 'date' ? 'YYYY-MM-DD' : '')"
        @update:value="(v: string) => set(cell.def.name, v)"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { NInput, NInputNumber, NSelect, NSpin, NSwitch } from "naive-ui";
import { CategoryAPI, type FieldDefinition, type FormLayout } from "@/api/repository";
import { DictAPI } from "@/api/dict";

const props = defineProps<{ categoryId: string | null; model: Record<string, unknown> }>();

const loading = ref(false);
const fields = ref<FieldDefinition[]>([]);
const layout = ref<FormLayout | null>(null);
const dictMap = ref<Record<string, { label: string; value: string }[]>>({});

const fieldMap = computed(() => {
  const m: Record<string, FieldDefinition> = {};
  fields.value.forEach((f) => { m[f.name] = f; });
  return m;
});

/** 行/格：优先用排版设计，没有则默认两列铺开 */
const renderRows = computed(() => {
  const rows = layout.value?.rows ?? [];
  if (rows.length) {
    return rows
      .map((r) => ({
        id: r.id,
        cells: r.cells.map((c) => ({ span: c.span, def: fieldMap.value[c.field] }))
          .filter((c): c is { span: 1 | 2; def: FieldDefinition } => !!c.def),
      }))
      .filter((r) => r.cells.length);
  }
  // 回退：按 sort_order 两列铺开；sort_order=0/缺失的(多为门类特殊字段)排到最后
  const ord = (f: FieldDefinition) => (f.sort_order && f.sort_order > 0 ? f.sort_order : 9999);
  const sorted = [...fields.value].sort((a, b) => ord(a) - ord(b));
  return [{ id: "fallback", cells: sorted.map((def) => ({ span: 1 as const, def })) }];
});

/** 摊平成单层格子，模板直接 grid 渲染（span 控制占列） */
const flatCells = computed(() => renderRows.value.flatMap((r) => r.cells));

function optionsFor(f: FieldDefinition) {
  if (f.options?.length) return f.options.map((o) => ({ label: o, value: o }));
  if (f.dict_type && dictMap.value[f.dict_type]) return dictMap.value[f.dict_type];
  return [];
}

function set(name: string, v: unknown) {
  // 父组件传入的是共享 reactive 模型，本组件作为表单绑定层写入它（约定如此）
  // eslint-disable-next-line vue/no-mutating-props
  props.model[name] = v;
}
const strVal = (v: unknown) => (v == null ? "" : String(v));
const strOrNull = (v: unknown) => (v == null || v === "" ? null : String(v));
const numOrNull = (v: unknown) => {
  if (v == null || v === "") return null;
  const n = Number(v);
  return Number.isNaN(n) ? null : n;
};

async function loadDicts(defs: FieldDefinition[]) {
  const types = [...new Set(defs.map((f) => f.dict_type).filter(Boolean) as string[])];
  await Promise.all(
    types.map(async (t) => {
      if (dictMap.value[t]) return;
      try {
        const r = await DictAPI.listItems(t);
        dictMap.value[t] = r.data.map((i) => ({ label: i.item_label, value: i.item_value }));
      } catch { /* 字典加载失败不阻断 */ }
    }),
  );
}

async function load(id: string | null) {
  if (!id) { fields.value = []; layout.value = null; return; }
  loading.value = true;
  try {
    const [schemaRes, layoutRes] = await Promise.all([
      CategoryAPI.getSchema(id),
      CategoryAPI.getLayout(id),
    ]);
    fields.value = schemaRes.data ?? [];
    layout.value = layoutRes.data ?? null;
    await loadDicts(fields.value);
    // 默认值：仅对当前为空的字段填入
    for (const f of fields.value) {
      if (f.default_value != null && (props.model[f.name] == null || props.model[f.name] === "")) {
        // eslint-disable-next-line vue/no-mutating-props
        props.model[f.name] = f.default_value;
      }
    }
  } finally {
    loading.value = false;
  }
}

watch(() => props.categoryId, (id) => load(id), { immediate: true });

/** 供父组件校验必填，返回缺失字段中文名列表 */
function validate(): string[] {
  return fields.value
    .filter((f) => f.required && (props.model[f.name] == null || props.model[f.name] === ""))
    .map((f) => f.label);
}

/** 当前门类的全部字段名（父组件拆 base/ext 用） */
function fieldNames(): string[] {
  return fields.value.map((f) => f.name);
}

defineExpose({ validate, fieldNames });
</script>
