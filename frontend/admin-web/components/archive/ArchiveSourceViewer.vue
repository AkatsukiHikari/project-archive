<template>
  <div class="flex flex-col h-full min-h-0">
    <!-- 工具栏 -->
    <div class="flex items-center gap-2 px-3 py-2 shrink-0 border-b border-gray-200">
      <Icon name="heroicons:document-text" class="w-4 h-4 text-indigo-600 shrink-0" />
      <span class="text-[13px] font-medium truncate">{{ title || "档案原文" }}</span>
      <code v-if="dh" class="text-[11px] font-mono px-1.5 py-0.5 rounded bg-gray-100 text-indigo-600">{{ dh }}</code>
      <div class="flex-1" />
      <NSelect v-if="attachments.length > 1" v-model:value="activeKey" :options="attOptions" size="small" style="width: 180px" />
      <NButton v-if="pdfUrl" text size="small" @click="openRaw">
        <template #icon><Icon name="heroicons:arrow-top-right-on-square" class="w-4 h-4" /></template>
      </NButton>
      <NButton v-if="allowCite" size="small" type="primary" @click="emit('insert-cite')">
        <template #icon><Icon name="heroicons:link" class="w-4 h-4" /></template>
        引用此档案
      </NButton>
    </div>

    <!-- 主体：PDF | 全文 -->
    <div class="flex-1 min-h-0 flex">
      <div ref="canvasWrap" class="flex-1 min-w-0 overflow-auto bg-gray-100 relative">
        <div v-if="loading" class="absolute inset-0 flex items-center justify-center"><NSpin /></div>
        <div v-else-if="!pdfUrl" class="absolute inset-0 flex flex-col items-center justify-center gap-2 text-gray-400">
          <Icon name="heroicons:document-magnifying-glass" class="w-10 h-10" />
          <p class="text-[13px]">该档案暂无数字化原文（PDF/OFD）</p>
        </div>
        <div v-else class="flex flex-col items-center gap-3 py-4">
          <ClientOnly>
            <VuePdfEmbed :source="pdfUrl" :width="pageWidth" @loaded="onLoaded" @loading-failed="onFailed" />
          </ClientOnly>
        </div>
      </div>

      <aside class="w-[360px] shrink-0 flex flex-col min-h-0 border-l border-gray-200">
        <div class="flex items-center gap-2 px-3 py-2 shrink-0 border-b border-gray-200">
          <Icon name="heroicons:sparkles" class="w-4 h-4 text-indigo-600" />
          <span class="text-[13px] font-semibold">OCR 全文</span>
          <span v-if="ocrText" class="text-[11px] text-green-600">已识别 · {{ ocrText.length }} 字</span>
          <span v-else-if="hasText" class="text-[11px] text-gray-400">PDF 文本层 · {{ totalChars }} 字</span>
          <div class="flex-1" />
          <NButton text size="tiny" :disabled="!ocrText && !hasText" @click="copyAll">
            <template #icon><Icon name="heroicons:clipboard-document" class="w-4 h-4" /></template>
            复制全文
          </NButton>
        </div>
        <div class="flex-1 min-h-0 overflow-y-auto px-3 py-2">
          <!-- 优先展示存下的 MinerU OCR 全文 -->
          <p
            v-if="ocrText"
            class="text-[12.5px] leading-relaxed whitespace-pre-wrap break-words text-gray-700 select-text"
          >{{ ocrText }}</p>
          <template v-else-if="extracting">
            <div class="flex items-center gap-2 py-6 text-[12px] text-gray-400"><NSpin size="small" /> 正在提取 PDF 文本层…</div>
          </template>
          <template v-else-if="hasText">
            <p class="text-[11px] text-amber-600 mb-2">（以下为 PDF 文本层提取，非 MinerU OCR 结果）</p>
            <p
              v-for="pt in pageTexts"
              :key="pt.page"
              class="text-[12.5px] leading-relaxed whitespace-pre-wrap break-words text-gray-700 mb-3 select-text"
            >{{ pt.text }}</p>
          </template>
          <div v-else class="flex flex-col items-center gap-2 py-8 text-center text-gray-400">
            <Icon name="heroicons:document-magnifying-glass" class="w-8 h-8" />
            <p class="text-[12px]">该档案尚未 OCR 识别</p>
            <p class="text-[11px]">挂接 PDF 会自动后台识别，或到「AI → OCR 任务」手动触发/查看进度</p>
          </div>
        </div>
      </aside>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { NButton, NSelect, NSpin, useMessage } from "naive-ui";
import VuePdfEmbed from "vue-pdf-embed";
import { ArchiveAPI, type ArchiveAttachment } from "@/api/repository";
import { AiAdminAPI } from "@/api/ai";

const props = withDefaults(
  defineProps<{ archiveId: string | null; title?: string; dh?: string; allowCite?: boolean }>(),
  { title: "", dh: "", allowCite: true },
);
const emit = defineEmits<{ (e: "insert-cite"): void }>();
const message = useMessage();

const attachments = ref<ArchiveAttachment[]>([]);
const activeKey = ref("");
const loading = ref(false);
const canvasWrap = ref<HTMLElement | null>(null);
const baseWidth = ref(720);

const activeAtt = computed(() => attachments.value.find((a) => a.id === activeKey.value) ?? null);
const pdfUrl = computed(() => activeAtt.value?.url ?? null);
const pageWidth = computed(() => baseWidth.value);
const attOptions = computed(() => attachments.value.map((a) => ({ label: a.original_name, value: a.id })));

interface PageText { page: number; text: string }
type PdfDocProxy = { numPages: number; getPage: (n: number) => Promise<{ getTextContent: () => Promise<{ items: Array<{ str?: string }> }> }> };
const extracting = ref(false);
const pageTexts = ref<PageText[]>([]);
let pdfDoc: PdfDocProxy | null = null;

// 存下的 MinerU OCR 全文（权威，优先展示）
const ocrText = ref("");

const hasText = computed(() => pageTexts.value.some((p) => p.text.trim().length > 0));
const totalChars = computed(() => pageTexts.value.reduce((s, p) => s + p.text.length, 0));
const fullText = computed(() => pageTexts.value.map((p) => p.text).join("\n\n"));

async function load() {
  if (!props.archiveId) return;
  loading.value = true;
  pageTexts.value = [];
  pdfDoc = null;
  ocrText.value = "";
  try {
    const res = await ArchiveAPI.attachments(props.archiveId);
    attachments.value = (res.data ?? []).filter((a) => a.url);
    activeKey.value = attachments.value[0]?.id ?? "";
    // 取存下的 OCR 全文（MinerU 结果）
    try {
      const t = await AiAdminAPI.ocrText(props.archiveId);
      ocrText.value = t.data.full_text || "";
    } catch {
      ocrText.value = "";
    }
  } finally {
    loading.value = false;
  }
}

async function onLoaded(doc: PdfDocProxy) {
  pdfDoc = doc;
  await extractText();
}
function onFailed() { message.error("原文加载失败"); }

async function extractText() {
  if (!pdfDoc) return;
  extracting.value = true;
  try {
    const out: PageText[] = [];
    for (let i = 1; i <= pdfDoc.numPages; i++) {
      const pg = await pdfDoc.getPage(i);
      const tc = await pg.getTextContent();
      out.push({ page: i, text: tc.items.map((it) => it.str ?? "").join(" ").replace(/[ \t]+/g, " ").trim() });
    }
    pageTexts.value = out;
  } finally {
    extracting.value = false;
  }
}

async function copyAll() {
  try {
    await navigator.clipboard.writeText(ocrText.value || fullText.value);
    message.success("全文已复制，可粘贴到正文");
  } catch {
    message.error("复制失败，请手动选择");
  }
}

function openRaw() { if (pdfUrl.value) window.open(pdfUrl.value, "_blank", "noopener"); }

watch(() => props.archiveId, () => { activeKey.value = ""; load(); }, { immediate: true });
watch(activeKey, () => { pageTexts.value = []; pdfDoc = null; });
</script>
