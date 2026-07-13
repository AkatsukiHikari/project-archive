<template>
  <NDrawer :show="show" :width="isFull ? '100%' : 1040" placement="right" @update:show="(v: boolean) => emit('update:show', v)">
    <NDrawerContent :body-content-style="{ padding: 0, height: '100%' }" closable>
      <template #header>
        <div class="flex items-center gap-2 w-full">
          <Icon name="heroicons:document-plus" class="w-5 h-5" style="color: oklch(var(--p))" />
          <span>智能著录校正</span>
          <code v-if="archive?.DH" class="text-[11px] font-mono px-1.5 py-0.5 rounded bg-gray-100" style="color: oklch(var(--p))">{{ archive.DH }}</code>
          <NTag v-if="archive" size="small" round :bordered="false" :type="archive.doc_source === 'formal' ? 'success' : 'default'">
            {{ archive.doc_source === 'formal' ? '正式库' : '暂存库' }}
          </NTag>
          <div class="flex-1" />
          <NButton text :title="isFull ? '退出全屏' : '全屏'" @click="isFull = !isFull">
            <Icon :name="isFull ? 'heroicons:arrows-pointing-in' : 'heroicons:arrows-pointing-out'" class="w-4 h-4" />
          </NButton>
        </div>
      </template>

      <div class="flex h-full min-h-0">
        <!-- 左：原文全文（档案系统核心，直接展示 AI 所读原文）+ PDF 原件入口 -->
        <div class="w-[460px] shrink-0 border-r flex flex-col min-h-0" style="border-color: var(--semi-color-border)">
          <div class="flex items-center gap-2 px-3 py-2 shrink-0 border-b" style="border-color: var(--semi-color-border)">
            <Icon name="heroicons:document-text" class="w-4 h-4" style="color: oklch(var(--p))" />
            <span class="text-[13px] font-medium" style="color: var(--semi-color-text-0)">OCR 识别全文</span>
            <span v-if="fullText" class="text-[11px] text-green-600">{{ fullText.length }} 字</span>
            <div class="flex-1" />
            <NButton text size="small" type="primary" :disabled="!archive" @click="openReader">
              <template #icon><Icon name="heroicons:document-magnifying-glass" class="w-4 h-4" /></template>
              查看原文
            </NButton>
          </div>
          <div class="flex-1 overflow-auto px-3 py-2 text-[12.5px] whitespace-pre-wrap break-words leading-relaxed" style="color: var(--semi-color-text-1)">
            <template v-if="fullText">{{ fullText }}</template>
            <span v-else style="color: var(--semi-color-text-3)">该档案暂无识别全文。可在右侧「立即 OCR 识别」后查看。</span>
          </div>
        </div>

        <!-- 右：著录表单 -->
        <div class="flex-1 min-w-0 flex flex-col min-h-0">
          <div v-if="loading" class="flex-1 flex items-center justify-center gap-2 text-sm" style="color: var(--semi-color-text-3)">
            <NSpin size="small" /> AI 正在阅读原文并比对著录字段…
          </div>

          <div v-else-if="errorMsg" class="flex-1 flex items-center justify-center px-6 text-center text-sm" style="color: #dc2626">{{ errorMsg }}</div>

          <template v-else>
            <!-- 无识别全文：手动编辑模式 + 就地 OCR -->
            <div v-if="needOcr" class="flex items-center gap-2 px-4 py-2 shrink-0" style="background: oklch(0.65 0.15 80/0.1)">
              <Icon name="heroicons:exclamation-triangle" class="w-4 h-4 shrink-0" style="color: oklch(0.6 0.18 80)" />
              <span class="text-[12.5px]" style="color: var(--semi-color-text-1)">暂无识别全文，当前为手动编辑；识别后可获得 AI 建议</span>
              <span v-if="ocrMsg" class="text-[11px]" :style="{ color: ocrFailed ? '#dc2626' : 'var(--semi-color-text-3)' }">{{ ocrMsg }}</span>
              <div class="flex-1" />
              <NButton size="tiny" type="warning" secondary :loading="ocrRunning" @click="runOcr">
                {{ ocrRunning ? '识别中…' : 'OCR 识别原文' }}
              </NButton>
            </div>
            <div v-else class="flex items-center gap-3 px-4 py-2.5 border-b shrink-0" style="border-color: var(--semi-color-border)">
              <span v-if="autoAdopt" class="text-[13px]" style="color: var(--semi-color-text-2)">
                AI 建议 <strong style="color: oklch(var(--p))">{{ changedCount }}</strong> 项（绿点）· 阈值 {{ threshold }}% 已自动采用
              </span>
              <span v-else class="text-[13px]" style="color: var(--semi-color-text-2)">
                AI 发现 <strong style="color: var(--semi-color-danger)">{{ changedCount }}</strong> 项与原文不符或缺录，表单保持现值，请逐项确认是否采用
              </span>
              <div class="flex-1" />
              <NButton size="tiny" tertiary @click="applyAllAi">全部采用 AI</NButton>
              <NButton size="tiny" tertiary @click="revertAll">还原</NButton>
            </div>

            <div class="flex-1 overflow-auto px-5 py-3">
              <!-- 按门类字段定义 + 排版设计渲染；AI 建议作字段附注 -->
              <ArchiveDynamicForm ref="dynRef" :category-id="archive?.category_id ?? null" :model="form">
                <template #field-extra="{ def }">
                  <div v-if="aiOf(def.name)" class="flex items-center gap-2 text-[11px] mt-0.5">
                    <template v-if="String(form[def.name] ?? '') === aiOf(def.name)!.suggested">
                      <NTag size="small" :type="aiOf(def.name)!.kind === 'fill' ? 'info' : 'warning'" round :bordered="false">
                        AI{{ aiOf(def.name)!.kind === 'fill' ? '补足' : '更正' }} {{ aiOf(def.name)!.confidence }}%<template v-if="aiOf(def.name)!.similarity !== null"> · 似{{ aiOf(def.name)!.similarity }}%</template>
                      </NTag>
                      <span v-if="aiOf(def.name)!.current" style="color: var(--semi-color-text-3)">原值：{{ aiOf(def.name)!.current }}</span>
                      <a class="cursor-pointer" style="color: var(--semi-color-text-3)" @click="form[def.name] = aiOf(def.name)!.current">撤销</a>
                    </template>
                    <template v-else>
                      <span style="color: var(--semi-color-text-3)">AI 建议：<strong style="color: oklch(var(--p))">{{ aiOf(def.name)!.suggested }}</strong>（{{ aiOf(def.name)!.confidence }}%）</span>
                      <a class="cursor-pointer" style="color: oklch(var(--p))" @click="form[def.name] = aiOf(def.name)!.suggested">采用</a>
                    </template>
                    <span v-if="aiOf(def.name)!.evidence" class="truncate" style="color: var(--semi-color-text-3)" :title="aiOf(def.name)!.evidence">· 依据：{{ aiOf(def.name)!.evidence }}</span>
                  </div>
                </template>
              </ArchiveDynamicForm>
            </div>

            <div class="flex items-center gap-2 px-4 py-3 border-t shrink-0" style="border-color: var(--semi-color-border)">
              <span class="text-[12px]" style="color: var(--semi-color-text-3)">将写入 {{ dirtyCount }} 个改动字段</span>
              <div class="flex-1" />
              <NButton size="small" @click="emit('update:show', false)">取消</NButton>
              <NButton size="small" type="primary" :disabled="dirtyCount === 0" :loading="applying" @click="doApply">保存著录</NButton>
            </div>
          </template>
        </div>
      </div>
    </NDrawerContent>

  </NDrawer>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { NButton, NDrawer, NDrawerContent, NSpin, NTag, useMessage } from "naive-ui";
import ArchiveDynamicForm from "./ArchiveDynamicForm.vue";
import { CatalogAPI, type FieldSuggestion } from "@/api/catalog";
import { AiAdminAPI } from "@/api/ai";

interface TargetArchive {
  id: string;
  doc_source: "staging" | "formal";
  DH?: string;
  TM: string;
  category_id?: string | null;
}

// 枚举编码字段不采用 AI 建议值（保持当前值，由用户在表单中调整）
const AI_SKIP = ["MJ", "BGQX"];

const props = withDefaults(
  defineProps<{
    show: boolean;
    archive: TargetArchive | null;
    /** 是否将 ≥阈值 的 AI 建议自动填入表单。著录补正=true；智能校对=false（只提示，逐项人工采用） */
    autoAdopt?: boolean;
  }>(),
  { autoAdopt: true },
);
const emit = defineEmits<{ (e: "update:show", v: boolean): void; (e: "applied"): void }>();

const message = useMessage();
const router = useRouter();

function openReader() {
  if (props.archive) router.push(`/archive/reader?id=${props.archive.id}`);
}

const loading = ref(false);
const applying = ref(false);
const needOcr = ref(false);
const errorMsg = ref("");
const threshold = ref(80);
const fullText = ref("");
const suggestions = ref<FieldSuggestion[]>([]);
const form = reactive<Record<string, unknown>>({});
const isFull = ref(false);
const dynRef = ref<{ validate: () => string[]; fieldNames: () => string[] } | null>(null);

// OCR 就地识别
const ocrRunning = ref(false);
const ocrFailed = ref(false);
const ocrMsg = ref("");

const sugMap = computed(() => {
  const m: Record<string, FieldSuggestion> = {};
  suggestions.value.forEach((s) => { m[s.name] = s; });
  return m;
});
function aiOf(name: string): FieldSuggestion | null {
  const s = sugMap.value[name];
  return s && s.changed && !AI_SKIP.includes(name) ? s : null;
}

const changedCount = computed(
  () => suggestions.value.filter((s) => s.changed && !AI_SKIP.includes(s.name)).length,
);
const dirtyCount = computed(
  () => suggestions.value.filter(
    (s) => String(form[s.name] ?? "").trim() !== (s.current ?? "").trim(),
  ).length,
);

function resetState() {
  needOcr.value = false;
  errorMsg.value = "";
  ocrFailed.value = false;
  ocrMsg.value = "";
  fullText.value = "";
  suggestions.value = [];
  for (const k of Object.keys(form)) form[k] = "";
}

async function load() {
  if (!props.archive) return;
  loading.value = true;
  resetState();
  try {
    const res = await CatalogAPI.suggest(props.archive.id, props.archive.doc_source);
    const d = res.data;
    if (!d.ok) {
      errorMsg.value = d.message || d.reason || "AI 著录失败";
      return;
    }
    needOcr.value = !!d.need_ocr;
    threshold.value = d.threshold ?? 80;
    fullText.value = d.full_text || "";
    suggestions.value = d.suggestions || [];
    for (const s of suggestions.value) {
      const useAi = props.autoAdopt && s.changed && s.preselect && !AI_SKIP.includes(s.name);
      form[s.name] = useAi ? s.suggested : s.current;
    }
  } catch {
    errorMsg.value = "请求失败，请确认 AI 服务是否正常";
  } finally {
    loading.value = false;
  }
}

function applyAllAi() {
  for (const s of suggestions.value) {
    if (s.changed && !AI_SKIP.includes(s.name)) form[s.name] = s.suggested;
  }
}
function revertAll() {
  for (const s of suggestions.value) form[s.name] = s.current;
}

// ── 就地 OCR：触发 + 轮询作业状态，完成后自动重新分析 ──────────────────────────
async function runOcr() {
  if (!props.archive) return;
  ocrRunning.value = true;
  ocrFailed.value = false;
  ocrMsg.value = "已提交识别任务…";
  try {
    const r = await AiAdminAPI.ocr(props.archive.id);
    if (!r.data.ok) {
      ocrFailed.value = true;
      ocrMsg.value = r.data.reason || "该档案没有可识别的 PDF 原文";
      ocrRunning.value = false;
      return;
    }
    await pollOcr();
  } catch {
    ocrFailed.value = true;
    ocrMsg.value = "OCR 触发失败";
    ocrRunning.value = false;
  }
}

async function pollOcr() {
  const id = props.archive?.id;
  if (!id) return;
  for (let i = 0; i < 30; i++) {
    await new Promise((r) => setTimeout(r, 3000));
    if (!props.show || props.archive?.id !== id) return;
    try {
      const jobs = (await AiAdminAPI.ocrJobs({ limit: 100 })).data.items;
      const job = jobs.find((j) => j.archive_id === id);
      if (job?.status === "succeeded") {
        ocrRunning.value = false;
        ocrMsg.value = "";
        await load();
        return;
      }
      if (job?.status === "failed") {
        ocrRunning.value = false;
        ocrFailed.value = true;
        ocrMsg.value = `OCR 失败：${job.error || "未知错误"}`;
        return;
      }
    } catch {
      /* 单次轮询失败忽略，继续 */
    }
  }
  ocrRunning.value = false;
  ocrFailed.value = true;
  ocrMsg.value = "识别超时，可到「OCR 任务」页查看进度后重试";
}

async function doApply() {
  if (!props.archive) return;
  const adopted: Record<string, string> = {};
  for (const s of suggestions.value) {
    const v = String(form[s.name] ?? "").trim();
    if (v !== (s.current ?? "").trim()) adopted[s.name] = v;
  }
  if (!Object.keys(adopted).length) return;
  applying.value = true;
  try {
    const res = await CatalogAPI.apply(props.archive.id, props.archive.doc_source, adopted);
    if (res.data.ok) {
      message.success(`已写入 ${res.data.changed ?? Object.keys(adopted).length} 个字段`);
      emit("applied");
      emit("update:show", false);
    } else {
      message.error(res.data.reason || "写入失败");
    }
  } catch {
    message.error("写入失败");
  } finally {
    applying.value = false;
  }
}

watch(
  () => [props.show, props.archive?.id] as const,
  ([show]) => {
    if (show && props.archive) load();
  },
);
</script>
