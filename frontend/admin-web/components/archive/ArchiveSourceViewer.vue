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
      <NButton size="small" type="primary" @click="emit('insert-cite')">
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
          <span v-if="hasText" class="text-[11px] text-gray-400">约 {{ totalChars }} 字</span>
          <div class="flex-1" />
          <NButton text size="tiny" :disabled="!hasText" @click="copyAll">
            <template #icon><Icon name="heroicons:clipboard-document" class="w-4 h-4" /></template>
            复制全文
          </NButton>
        </div>
        <div class="flex-1 min-h-0 overflow-y-auto px-3 py-2">
          <div v-if="extracting" class="flex items-center gap-2 py-6 text-[12px] text-gray-400"><NSpin size="small" /> 正在提取全文…</div>
          <template v-else-if="hasText">
            <p
              v-for="pt in pageTexts"
              :key="pt.page"
              class="text-[12.5px] leading-relaxed whitespace-pre-wrap break-words text-gray-700 mb-3 select-text"
            >{{ pt.text }}</p>
          </template>
          <div v-else-if="pdfUrl" class="flex flex-col items-center gap-2 py-8 text-center text-gray-400">
            <Icon name="heroicons:photo" class="w-8 h-8" />
            <p class="text-[12px]">该原文无文本层（疑为扫描件）</p>
            <p class="text-[11px]">写作时可直接参照左侧 PDF 影像</p>
          </div>
          <div v-else class="py-8 text-center text-[12px] text-gray-400">无原文可提取</div>
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

const props = defineProps<{ archiveId: string | null; title?: string; dh?: string }>();
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

const hasText = computed(() => pageTexts.value.some((p) => p.text.trim().length > 0));
const totalChars = computed(() => pageTexts.value.reduce((s, p) => s + p.text.length, 0));
const fullText = computed(() => pageTexts.value.map((p) => p.text).join("\n\n"));

async function load() {
  if (!props.archiveId) return;
  loading.value = true;
  pageTexts.value = [];
  pdfDoc = null;
  try {
    const res = await ArchiveAPI.attachments(props.archiveId);
    attachments.value = (res.data ?? []).filter((a) => a.url);
    activeKey.value = attachments.value[0]?.id ?? "";
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
    await navigator.clipboard.writeText(fullText.value);
    message.success("全文已复制，可粘贴到正文");
  } catch {
    message.error("复制失败，请手动选择");
  }
}

function openRaw() { if (pdfUrl.value) window.open(pdfUrl.value, "_blank", "noopener"); }

watch(() => props.archiveId, () => { activeKey.value = ""; load(); }, { immediate: true });
watch(activeKey, () => { pageTexts.value = []; pdfDoc = null; });
</script>
