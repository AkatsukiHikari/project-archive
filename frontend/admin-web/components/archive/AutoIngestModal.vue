<template>
  <NModal :show="show" @update:show="(v: boolean) => emit('update:show', v)">
    <NCard style="width: 680px; max-width: 92vw" :bordered="false" role="dialog" closable @close="emit('update:show', false)">
      <template #header>
        <div class="flex items-center gap-2">
          <Icon name="heroicons:sparkles" class="w-5 h-5" style="color: oklch(var(--p))" />
          <span>自动录入 · AI 识别数字化成果</span>
        </div>
      </template>

      <!-- 第一步：选门类 + 上传 -->
      <div v-if="phase === 'form'" class="flex flex-col gap-3">
        <div class="grid grid-cols-3 gap-3">
          <Field label="全宗"><NSelect v-model:value="fondsId" :options="fondsOptions" placeholder="选择全宗" filterable @update:value="onFonds" /></Field>
          <Field label="目录"><NSelect v-model:value="catalogId" :options="catalogOptions" placeholder="选择目录" :disabled="!fondsId" /></Field>
          <Field label="门类"><NSelect v-model:value="categoryId" :options="categoryOptions" placeholder="选择门类" filterable /></Field>
        </div>
        <NUpload :max="1" :default-upload="false" accept=".pdf,.ofd,.PDF,.OFD" @change="onFileChange">
          <NUploadDragger>
            <Icon name="heroicons:document-arrow-up" class="w-8 h-8 mx-auto" style="color: var(--semi-color-text-3)" />
            <p class="text-[13px] mt-2" style="color: var(--semi-color-text-2)">点击或拖拽上传 PDF / OFD 数字化成果</p>
          </NUploadDragger>
        </NUpload>
        <div class="flex justify-end gap-2 pt-1">
          <NButton @click="emit('update:show', false)">取消</NButton>
          <NButton type="primary" :disabled="!canAnalyze" @click="analyze">
            <template #icon><Icon name="heroicons:sparkles" class="w-4 h-4" /></template>
            AI 识别
          </NButton>
        </div>
      </div>

      <!-- 第二步：识别中 -->
      <div v-else-if="phase === 'analyzing'" class="flex flex-col items-center justify-center gap-3 py-10">
        <NSpin />
        <p class="text-sm" style="color: var(--semi-color-text-2)">AI 正在 OCR 识别原文并抽取著录字段，请稍候…</p>
        <p class="text-[12px]" style="color: var(--semi-color-text-3)">扫描件识别较慢，通常 10~60 秒</p>
      </div>

      <!-- 第三步：确认表单 -->
      <div v-else class="flex flex-col gap-3">
        <p class="text-[12px]" style="color: var(--semi-color-text-3)">AI 已识别 {{ chars }} 字并填入下列字段，请核对修改后入库（暂存库草稿）。</p>
        <div class="max-h-[50vh] overflow-auto flex flex-col gap-2.5 pr-1">
          <div v-for="r in rows" :key="r.name" class="grid grid-cols-[88px_1fr_48px] items-center gap-2">
            <span class="text-[13px] text-right" style="color: var(--semi-color-text-2)">
              {{ r.label }}<span v-if="r.required" style="color:#dc2626">*</span>
            </span>
            <NSelect v-if="r.options && r.options.length" :value="vals[r.name]" :options="r.options.map((o) => ({ label: o, value: o }))" size="small" clearable @update:value="(v: string) => (vals[r.name] = v)" />
            <NInput v-else :value="vals[r.name]" size="small" @update:value="(v: string) => (vals[r.name] = v)" />
            <span class="text-[11px] tabular-nums text-right" :style="{ color: r.confidence >= threshold ? 'oklch(var(--su))' : 'var(--semi-color-text-3)' }">{{ r.confidence }}%</span>
          </div>
        </div>
        <div class="flex justify-end gap-2 pt-1">
          <NButton @click="phase = 'form'">上一步</NButton>
          <NButton type="primary" :loading="saving" @click="submit">确认新增入库</NButton>
        </div>
      </div>
    </NCard>
  </NModal>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from "vue";
import { NButton, NCard, NInput, NModal, NSelect, NSpin, NUpload, NUploadDragger, useMessage } from "naive-ui";
import type { UploadFileInfo } from "naive-ui";
import { CatalogAPI, type FieldSuggestion } from "@/api/catalog";
import { CategoryAPI, FondsAPI, CatalogAPI as CatalogDirAPI } from "@/api/repository";
import type { ArchiveCreate, ArchiveCategory, Catalog, Fonds } from "@/api/repository";

const props = defineProps<{ show: boolean }>();
const emit = defineEmits<{ (e: "update:show", v: boolean): void; (e: "created"): void }>();

const message = useMessage();

const BASE_TEXT = ["TM", "QZH", "DH", "RZZ", "WJRQ"];
const BASE_NUM = ["ND", "YS"];
const SKIP_ENUM = ["MJ", "BGQX"]; // 枚举编码字段不自动入库，用默认值，著录页再调

const phase = ref<"form" | "analyzing" | "review">("form");
const fondsId = ref<string | null>(null);
const catalogId = ref<string | null>(null);
const categoryId = ref<string | null>(null);
const file = ref<File | null>(null);
const chars = ref(0);
const threshold = ref(80);
const saving = ref(false);

const fondsList = ref<Fonds[]>([]);
const catalogList = ref<Catalog[]>([]);
const categoryList = ref<ArchiveCategory[]>([]);
const fondsOptions = computed(() => fondsList.value.map((f) => ({ label: `${f.fonds_code} - ${f.name}`, value: f.id })));
const catalogOptions = computed(() => catalogList.value.map((c) => ({ label: c.name, value: c.id })));
const categoryOptions = computed(() => categoryList.value.map((c) => ({ label: `${c.code} - ${c.name}`, value: c.id })));

const rows = ref<FieldSuggestion[]>([]);
const vals = reactive<Record<string, string>>({});
const fullTextVal = ref("");

const canAnalyze = computed(() => !!(fondsId.value && catalogId.value && categoryId.value && file.value));

async function loadOptions() {
  const [f, c] = await Promise.all([FondsAPI.list(), CategoryAPI.list()]);
  fondsList.value = f.data;
  categoryList.value = c.data;
}

async function onFonds(id: string) {
  catalogId.value = null;
  catalogList.value = id ? (await CatalogDirAPI.list(id)).data : [];
  const fonds = fondsList.value.find((x) => x.id === id);
  if (fonds && !vals.QZH) vals.QZH = fonds.fonds_code;
}

function onFileChange(data: { fileList: UploadFileInfo[] }) {
  file.value = data.fileList[0]?.file ?? null;
}

async function analyze() {
  if (!canAnalyze.value || !file.value || !categoryId.value) return;
  phase.value = "analyzing";
  try {
    const res = await CatalogAPI.extract(file.value, categoryId.value);
    const d = res.data;
    if (!d.ok) {
      message.error(d.reason || "AI 识别失败");
      phase.value = "form";
      return;
    }
    threshold.value = d.threshold ?? 80;
    chars.value = d.chars ?? 0;
    rows.value = (d.suggestions || []).filter((s) => !SKIP_ENUM.includes(s.name));
    for (const r of rows.value) vals[r.name] = r.suggested;
    fullTextVal.value = d.full_text || "";
    // 档号用系统下一个号（末位+1）预填，覆盖 AI 的猜测；用户可手改
    if (d.suggested_dh) vals.DH = d.suggested_dh;
    // 全宗号兜底用所选全宗 code
    if (!vals.QZH) {
      const fonds = fondsList.value.find((x) => x.id === fondsId.value);
      if (fonds) vals.QZH = fonds.fonds_code;
    }
    phase.value = "review";
  } catch {
    message.error("AI 识别失败，请确认 AI 服务是否正常");
    phase.value = "form";
  }
}

async function submit() {
  if (!fondsId.value || !catalogId.value || !categoryId.value) return;
  if (!file.value) return message.error("缺少上传文件，请重新识别");
  if (!vals.TM?.trim()) return message.error("题名（TM）必填");
  if (!vals.QZH?.trim()) return message.error("全宗号（QZH）必填");
  if (!vals.DH?.trim()) return message.error("档号必填，没有档号不可入库");

  const ext: Record<string, unknown> = {};
  const payload: ArchiveCreate = {
    fonds_id: fondsId.value,
    catalog_id: catalogId.value,
    category_id: categoryId.value,
    TM: vals.TM.trim(),
    QZH: vals.QZH.trim(),
  } as ArchiveCreate;
  for (const r of rows.value) {
    const v = (vals[r.name] ?? "").trim();
    if (!v) continue;
    if (r.name === "TM" || r.name === "QZH") continue;
    if (BASE_TEXT.includes(r.name)) (payload as Record<string, unknown>)[r.name] = v;
    else if (BASE_NUM.includes(r.name)) { const n = Number(v); if (!Number.isNaN(n)) (payload as Record<string, unknown>)[r.name] = n; }
    else ext[r.name] = v;
  }
  if (Object.keys(ext).length) payload.ext_fields = ext;

  saving.value = true;
  try {
    const res = await CatalogAPI.ingest(file.value, { ...payload, full_text: fullTextVal.value });
    if (res.code === 0) {
      message.success(`已新增入暂存库：${res.data.DH || res.data.TM}`);
      emit("created");
      emit("update:show", false);
    } else {
      message.error(res.message || "新增失败");
    }
  } catch {
    message.error("新增失败");
  } finally {
    saving.value = false;
  }
}

function reset() {
  phase.value = "form";
  fondsId.value = catalogId.value = categoryId.value = null;
  file.value = null;
  rows.value = [];
  fullTextVal.value = "";
  for (const k of Object.keys(vals)) vals[k] = "";
}

watch(
  () => props.show,
  (v) => {
    if (v) {
      reset();
      if (!fondsList.value.length) loadOptions();
    }
  },
);
</script>
