<template>
  <NModal :show="show" @update:show="(v: boolean) => emit('update:show', v)">
    <NCard
      :style="isFull ? 'width:96vw;height:92vh' : 'width:820px;max-width:94vw'"
      :bordered="false"
      role="dialog"
      closable
      class="flex flex-col"
      :content-style="isFull ? 'flex:1;min-height:0;overflow:hidden;display:flex;flex-direction:column' : ''"
      @close="emit('update:show', false)"
    >
      <template #header>
        <div class="flex items-center gap-2">
          <Icon name="heroicons:sparkles" class="w-5 h-5" style="color: oklch(var(--p))" />
          <span>自动录入 · AI 识别数字化成果</span>
        </div>
      </template>
      <template #header-extra>
        <NButton text :title="isFull ? '退出全屏' : '全屏'" @click="isFull = !isFull">
          <Icon :name="isFull ? 'heroicons:arrows-pointing-in' : 'heroicons:arrows-pointing-out'" class="w-4 h-4" />
        </NButton>
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

      <!-- 第三步：确认表单（按门类字段定义 + 排版设计渲染） -->
      <div v-else class="flex flex-col gap-3" :class="isFull ? 'flex-1 min-h-0' : ''">
        <p class="text-[12px] m-0" style="color: var(--semi-color-text-3)">AI 已识别 {{ chars }} 字并填入下列字段，请核对修改后入库。</p>
        <div class="overflow-auto pr-1" :class="isFull ? 'flex-1 min-h-0' : 'max-h-[56vh]'">
          <ArchiveDynamicForm ref="dynRef" :category-id="categoryId" :model="vals">
            <template #field-extra="{ def }">
              <div v-if="confOf(def.name) !== null" class="mt-0.5 text-[11px] tabular-nums" :style="{ color: (confOf(def.name) ?? 0) >= threshold ? 'oklch(var(--su))' : 'var(--semi-color-text-3)' }">
                AI 置信 {{ confOf(def.name) }}%
              </div>
            </template>
          </ArchiveDynamicForm>
        </div>
        <div class="flex justify-end gap-2 pt-1 shrink-0">
          <NButton @click="phase = 'form'">上一步</NButton>
          <NButton type="primary" :loading="saving" @click="submit">确认新增入库</NButton>
        </div>
      </div>
    </NCard>
  </NModal>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from "vue";
import { NButton, NCard, NModal, NSelect, NSpin, NUpload, NUploadDragger, useMessage } from "naive-ui";
import type { UploadFileInfo } from "naive-ui";
import ArchiveDynamicForm from "./ArchiveDynamicForm.vue";
import { CatalogAPI, type FieldSuggestion } from "@/api/catalog";
import { CategoryAPI, FondsAPI, CatalogAPI as CatalogDirAPI } from "@/api/repository";
import type { ArchiveCreate, ArchiveCategory, Catalog, Fonds } from "@/api/repository";

const props = defineProps<{ show: boolean }>();
const emit = defineEmits<{ (e: "update:show", v: boolean): void; (e: "created"): void }>();

const message = useMessage();

// 映射到档案表列的字段，其余进 ext_fields
const BASE_TEXT = ["TM", "QZH", "DH", "RZZ", "WJRQ", "MJ", "BGQX"];
const BASE_NUM = ["ND", "YS"];
// 枚举编码字段不用 AI 建议值（取门类默认值，由用户确认）
const AI_SKIP = ["MJ", "BGQX"];

const isFull = ref(false);
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

const suggestions = ref<FieldSuggestion[]>([]);
const vals = reactive<Record<string, unknown>>({});
const fullTextVal = ref("");
const dynRef = ref<{ validate: () => string[]; fieldNames: () => string[] } | null>(null);

const sugMap = computed(() => {
  const m: Record<string, FieldSuggestion> = {};
  suggestions.value.forEach((s) => { m[s.name] = s; });
  return m;
});
function confOf(name: string): number | null {
  const s = sugMap.value[name];
  return s && s.suggested ? s.confidence : null;
}

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
    fullTextVal.value = d.full_text || "";
    suggestions.value = d.suggestions || [];
    for (const s of suggestions.value) {
      if (s.suggested && !AI_SKIP.includes(s.name)) vals[s.name] = s.suggested;
    }
    // 档号用系统生成的下一个号覆盖 AI 猜测；全宗号兜底取所选全宗
    if (d.suggested_dh) vals.DH = d.suggested_dh;
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
  const s = (k: string) => (vals[k] == null ? "" : String(vals[k]).trim());
  if (!s("TM")) return message.error("题名（TM）必填");
  if (!s("QZH")) return message.error("全宗号（QZH）必填");
  if (!s("DH")) return message.error("档号必填，没有档号不可入库");
  const missing = dynRef.value?.validate() ?? [];
  if (missing.length) return message.error(`请填写必录字段：${missing.join("、")}`);

  const names = dynRef.value?.fieldNames() ?? Object.keys(vals);
  const ext: Record<string, unknown> = {};
  const payload: ArchiveCreate = {
    fonds_id: fondsId.value,
    catalog_id: catalogId.value,
    category_id: categoryId.value,
    TM: s("TM"),
    QZH: s("QZH"),
  } as ArchiveCreate;
  for (const name of names) {
    const v = s(name);
    if (!v || name === "TM" || name === "QZH") continue;
    if (BASE_TEXT.includes(name)) (payload as Record<string, unknown>)[name] = v;
    else if (BASE_NUM.includes(name)) { const n = Number(v); if (!Number.isNaN(n)) (payload as Record<string, unknown>)[name] = n; }
    else ext[name] = vals[name];
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
  suggestions.value = [];
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
