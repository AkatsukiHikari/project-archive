<template>
  <div class="flex flex-col h-full min-h-0">
    <!-- ── 顶部工具栏 ─────────────────────────────────────────── -->
    <div
      class="flex items-center gap-2 px-3 py-2 shrink-0"
      style="background:var(--semi-color-bg-0);border-bottom:1px solid var(--semi-color-border)"
    >
      <NButton quaternary size="small" @click="goBack">
        <template #icon><Icon name="heroicons:arrow-left" class="w-4 h-4" /></template>
        返回
      </NButton>

      <div class="min-w-0 flex items-center gap-2">
        <Icon name="heroicons:document-text" class="w-4 h-4 shrink-0" style="color:oklch(var(--p))" />
        <span class="text-[13px] font-medium truncate" style="color:var(--semi-color-text-0)">
          {{ archive?.TM || "档案原文" }}
        </span>
        <code v-if="archive?.DH" class="text-[11px] font-mono px-1.5 py-0.5 rounded" style="background:var(--semi-color-fill-0);color:oklch(var(--p))">{{ archive.DH }}</code>
      </div>

      <div class="flex-1" />

      <NSelect
        v-if="attachments.length > 1"
        v-model:value="activeKey"
        :options="attachmentOptions"
        size="small"
        style="width: 200px"
      />

      <template v-if="pdfUrl">
        <span class="text-[12px] tabular-nums px-1" style="color:var(--semi-color-text-2)">{{ currentPage }} / {{ pageCount || "…" }}</span>

        <div class="flex items-center gap-0.5 px-1.5 rounded-lg" style="background:var(--semi-color-fill-0)">
          <NTooltip><template #trigger><NButton text size="small" @click="zoomOut"><Icon name="heroicons:minus" class="w-4 h-4" /></NButton></template>缩小</NTooltip>
          <span class="text-[12px] tabular-nums px-1 cursor-pointer" style="color:var(--semi-color-text-1)" @click="resetZoom">{{ Math.round(zoom * 100) }}%</span>
          <NTooltip><template #trigger><NButton text size="small" @click="zoomIn"><Icon name="heroicons:plus" class="w-4 h-4" /></NButton></template>放大</NTooltip>
        </div>

        <NTooltip><template #trigger><NButton text size="small" @click="fitWidth"><Icon name="heroicons:arrows-pointing-out" class="w-4 h-4" /></NButton></template>适应宽度</NTooltip>
        <NTooltip><template #trigger><NButton text size="small" @click="rotate"><Icon name="heroicons:arrow-path" class="w-4 h-4" /></NButton></template>旋转</NTooltip>
        <NTooltip><template #trigger><NButton text size="small" @click="printPdf"><Icon name="heroicons:printer" class="w-4 h-4" /></NButton></template>打印</NTooltip>
        <NTooltip><template #trigger><NButton text size="small" @click="download"><Icon name="heroicons:arrow-down-tray" class="w-4 h-4" /></NButton></template>下载</NTooltip>
        <NTooltip><template #trigger><NButton text size="small" @click="openRaw"><Icon name="heroicons:arrow-top-right-on-square" class="w-4 h-4" /></NButton></template>新窗口打开</NTooltip>
        <NButton
          size="small"
          :type="showText ? 'primary' : 'default'"
          :secondary="!showText"
          @click="toggleText"
        >
          <template #icon><Icon name="heroicons:document-magnifying-glass" class="w-4 h-4" /></template>
          全文
        </NButton>
      </template>
    </div>

    <!-- ── 主体：左 元数据 / 中 PDF / 右 全文（三栏各自独立滚动） ─────── -->
    <div class="flex-1 min-h-0 flex overflow-hidden">
      <!-- 左：可折叠档案基本数据（独立滚动，不随 PDF 滚动） -->
      <button
        v-if="infoCollapsed"
        class="w-9 shrink-0 flex flex-col items-center gap-2 pt-3 cursor-pointer border-none"
        style="background:var(--semi-color-bg-0);border-right:1px solid var(--semi-color-border)"
        title="展开档案信息"
        @click="toggleInfo"
      >
        <Icon name="heroicons:chevron-double-right" class="w-4 h-4" style="color:oklch(var(--p))" />
        <span class="text-[11px]" style="color:var(--semi-color-text-2);writing-mode:vertical-rl;letter-spacing:2px">档案信息</span>
      </button>
      <aside
        v-else
        class="w-[320px] shrink-0 overflow-y-auto p-4 flex flex-col gap-4"
        style="background:var(--semi-color-bg-0);border-right:1px solid var(--semi-color-border)"
      >
        <div class="flex items-center gap-2">
          <Icon name="heroicons:identification" class="w-4 h-4 shrink-0" style="color:oklch(var(--p))" />
          <span class="text-[13px] font-semibold" style="color:var(--semi-color-text-0)">档案基本信息</span>
          <div class="flex-1" />
          <NTooltip>
            <template #trigger>
              <NButton text size="tiny" @click="toggleInfo">
                <Icon name="heroicons:chevron-double-left" class="w-4 h-4" />
              </NButton>
            </template>
            收起
          </NTooltip>
        </div>

        <!-- AI 摘要 -->
        <div class="rounded-lg border p-3 flex flex-col gap-2" style="border-color: oklch(var(--p)/0.25); background: oklch(var(--p)/0.05)">
          <div class="flex items-center gap-1.5">
            <Icon name="heroicons:sparkles" class="w-4 h-4" style="color:oklch(var(--p))" />
            <span class="text-[12.5px] font-semibold" style="color:var(--semi-color-text-0)">AI 摘要</span>
            <div class="flex-1" />
            <NButton v-if="sumStatus === 'ready'" text size="tiny" type="primary" title="把摘要写入本档案的「摘要」著录字段" @click="fillZY">
              填入摘要字段
            </NButton>
          </div>
          <p v-if="sumStatus === 'ready'" class="text-[12.5px] leading-relaxed whitespace-pre-wrap break-words m-0" style="color:var(--semi-color-text-1)">{{ sumText }}</p>
          <div v-else-if="sumStatus === 'loading'" class="flex items-center gap-2 text-[12px]" style="color:var(--semi-color-text-3)">
            <NSpin size="small" /> 正在生成摘要…
          </div>
          <div v-else-if="sumStatus === 'ocr'" class="flex items-center gap-2 text-[12px]" style="color:var(--semi-color-text-3)">
            <NSpin size="small" /> 正在识别原文（OCR），完成后自动生成摘要…
          </div>
          <div v-else-if="sumStatus === 'ocr_failed'" class="flex flex-col gap-1">
            <p class="text-[12px] m-0" style="color:#dc2626">OCR 识别失败：{{ sumError }}</p>
            <div>
              <NButton text size="tiny" type="primary" @click="retryOcr">重试识别</NButton>
            </div>
          </div>
          <p v-else-if="sumStatus === 'no_source'" class="text-[12px] m-0" style="color:var(--semi-color-text-3)">该档案未挂接数字化原文，无法生成摘要</p>
          <div v-else-if="sumStatus === 'error'" class="flex items-center gap-2 text-[12px]" style="color:#dc2626">
            摘要生成失败
            <NButton text size="tiny" type="primary" @click="fetchSummary">重试</NButton>
          </div>
        </div>

        <div v-if="archive" class="flex flex-col">
          <div
            v-for="f in metaFields"
            :key="f.label"
            class="grid grid-cols-[84px_1fr] gap-2 py-2 text-[12.5px]"
            style="border-bottom:1px dashed var(--semi-color-border)"
          >
            <span style="color:var(--semi-color-text-3)">{{ f.label }}</span>
            <span class="break-words" :class="f.mono ? 'font-mono' : ''" style="color:var(--semi-color-text-0)">{{ f.value || "—" }}</span>
          </div>

          <template v-if="extEntries.length">
            <div class="mt-3 mb-1 text-[12px] font-medium" style="color:var(--semi-color-text-2)">门类字段</div>
            <div
              v-for="[k, v] in extEntries"
              :key="k"
              class="grid grid-cols-[84px_1fr] gap-2 py-2 text-[12.5px]"
              style="border-bottom:1px dashed var(--semi-color-border)"
            >
              <span style="color:var(--semi-color-text-3)">{{ k }}</span>
              <span class="break-words" style="color:var(--semi-color-text-0)">{{ String(v) }}</span>
            </div>
          </template>
        </div>
        <NSpin v-else size="small" />
      </aside>

      <!-- 中：PDF 竖向连续渲染 -->
      <div ref="canvasWrap" class="flex-1 min-w-0 overflow-auto relative" style="background:var(--semi-color-fill-1)" @scroll="onScroll">
        <div v-if="loading" class="absolute inset-0 flex items-center justify-center">
          <NSpin size="large" />
        </div>

        <div v-else-if="!pdfUrl" class="absolute inset-0 flex flex-col items-center justify-center gap-3" style="color:var(--semi-color-text-3)">
          <Icon name="heroicons:document-magnifying-glass" class="w-12 h-12" />
          <p class="text-[13px]">该档案暂无可在线预览的原文附件</p>
        </div>

        <div v-else class="pdf-scroll flex flex-col items-center gap-3 py-5">
          <ClientOnly>
            <VuePdfEmbed
              :source="pdfUrl"
              :width="pageWidth"
              :rotation="rotation"
              @loaded="onLoaded"
              @loading-failed="onFailed"
            />
          </ClientOnly>
        </div>
      </div>

      <!-- 右：全文（OCR/文本层）面板 -->
      <aside
        v-if="showText"
        class="w-[380px] shrink-0 flex flex-col min-h-0"
        style="background:var(--semi-color-bg-0);border-left:1px solid var(--semi-color-border)"
      >
        <div class="flex items-center gap-2 px-3 py-2.5 shrink-0" style="border-bottom:1px solid var(--semi-color-border)">
          <Icon name="heroicons:sparkles" class="w-4 h-4" style="color:oklch(var(--p))" />
          <span class="text-[13px] font-semibold" style="color:var(--semi-color-text-0)">档案全文</span>
          <span v-if="serverText" class="text-[11px]" style="color:oklch(var(--su))">OCR 已识别 · {{ totalChars }} 字</span>
          <span v-else-if="hasText" class="text-[11px]" style="color:var(--semi-color-text-3)">PDF 文本层 · 约 {{ totalChars }} 字</span>
          <div class="flex-1" />
          <NButton text size="tiny" :disabled="!hasText" @click="copyAll">
            <template #icon><Icon name="heroicons:clipboard-document" class="w-4 h-4" /></template>
            复制全文
          </NButton>
        </div>

        <div v-if="hasText" class="px-3 py-2 shrink-0">
          <NInput v-model:value="textQuery" size="small" placeholder="在全文中搜索…" clearable>
            <template #prefix><Icon name="heroicons:magnifying-glass" class="w-3.5 h-3.5" style="color:var(--semi-color-text-3)" /></template>
          </NInput>
          <div v-if="textQuery" class="text-[11px] mt-1" style="color:var(--semi-color-text-3)">命中 {{ matchCount }} 处</div>
        </div>

        <div class="flex-1 min-h-0 overflow-y-auto px-3 pb-4">
          <!-- 优先：服务端 OCR 识别全文 -->
          <template v-if="serverText">
            <!-- eslint-disable-next-line vue/no-v-html -->
            <p
              class="text-[12.5px] leading-relaxed whitespace-pre-wrap break-words ocr-text pt-2"
              style="color:var(--semi-color-text-1)"
              v-html="highlight(serverText)"
            />
          </template>
          <div v-else-if="extracting" class="flex items-center gap-2 py-6 text-[12px]" style="color:var(--semi-color-text-3)">
            <NSpin size="small" /> 正在提取全文…
          </div>
          <!-- 回退：PDF 自带文本层 -->
          <template v-else-if="hasText">
            <div v-for="pt in pageTexts" :key="pt.page" class="mb-4">
              <div class="text-[11px] mb-1 font-medium" style="color:var(--semi-color-text-3)">第 {{ pt.page }} 页</div>
              <!-- eslint-disable-next-line vue/no-v-html -->
              <p
                class="text-[12.5px] leading-relaxed whitespace-pre-wrap break-words ocr-text"
                style="color:var(--semi-color-text-1)"
                v-html="highlight(pt.text)"
              />
            </div>
          </template>
          <!-- OCR 进行中（由 AI 摘要状态机驱动，完成后自动刷新） -->
          <div v-else-if="sumStatus === 'ocr'" class="flex flex-col items-center gap-2 py-8 text-center" style="color:var(--semi-color-text-3)">
            <NSpin size="small" />
            <p class="text-[12px]">正在 OCR 识别原文，完成后自动显示全文…</p>
          </div>
          <div v-else class="flex flex-col items-center gap-2 py-8 text-center" style="color:var(--semi-color-text-3)">
            <Icon name="heroicons:photo" class="w-8 h-8" />
            <p class="text-[12px]">暂无识别全文（扫描件需 OCR 识别）</p>
            <p class="text-[11px]">可在「AI → OCR 任务」查看识别进度，或稍后刷新</p>
          </div>
        </div>
      </aside>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, onDeactivated, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { NButton, NInput, NSelect, NSpin, NTooltip, useMessage } from "naive-ui";
import VuePdfEmbed from "vue-pdf-embed";
import { ArchiveAPI } from "@/api/repository";
import type { Archive, ArchiveAttachment } from "@/api/repository";
import { AiAdminAPI } from "@/api/ai";

definePageMeta({ layout: "archive", middleware: "auth" });

const route = useRoute();
const router = useRouter();
const message = useMessage();

const archiveId = computed(() => String(route.query.id ?? ""));

const archive = ref<Archive | null>(null);
const attachments = ref<ArchiveAttachment[]>([]);
const activeKey = ref<string>("");
const loading = ref(true);

// ── AI 摘要：有全文即生成(带缓存)；无全文自动触发 OCR 后轮询 ────────────────
const sumStatus = ref<"idle" | "loading" | "ready" | "ocr" | "ocr_failed" | "no_source" | "error">("idle");
const sumText = ref("");
const sumError = ref("");
let sumTimer: ReturnType<typeof setTimeout> | null = null;
let sumPollCount = 0;
const SUM_POLL_MAX = 40; // 约 5 分钟

function stopSumPoll() {
  if (sumTimer) { clearTimeout(sumTimer); sumTimer = null; }
}

async function fetchSummary() {
  if (!archiveId.value) return;
  stopSumPoll();
  if (sumStatus.value !== "ocr") { sumStatus.value = "loading"; sumPollCount = 0; }
  try {
    const res = await AiAdminAPI.summary(archiveId.value);
    const d = res.data;
    if (d.status === "ready") {
      sumText.value = d.summary || "";
      sumStatus.value = "ready";
      // OCR 刚完成的场景：同步刷新右侧全文面板
      if (!serverText.value) loadServerText();
      return;
    }
    if (d.status === "ocr_running" || d.status === "ocr_started") {
      if (++sumPollCount > SUM_POLL_MAX) {
        sumStatus.value = "ocr_failed";
        sumError.value = "识别等待超时，可点击重试";
        return;
      }
      sumStatus.value = "ocr";
      sumTimer = setTimeout(fetchSummary, 8000);
      return;
    }
    if (d.status === "ocr_failed") {
      sumStatus.value = "ocr_failed";
      sumError.value = d.message || "OCR 识别失败";
      return;
    }
    sumStatus.value = "no_source";
  } catch {
    sumStatus.value = "error";
  }
}

/** OCR 失败后手动重试：强制投递新任务并恢复轮询 */
async function retryOcr() {
  if (!archiveId.value) return;
  sumStatus.value = "ocr";
  sumPollCount = 0;
  try {
    await AiAdminAPI.ocr(archiveId.value);
    sumTimer = setTimeout(fetchSummary, 5000);
  } catch {
    sumStatus.value = "ocr_failed";
    sumError.value = "重试触发失败";
  }
}

/** 把摘要写入本档案的「摘要(ZY)」著录字段 */
async function fillZY() {
  if (!archive.value || !sumText.value) return;
  try {
    await ArchiveAPI.update(archive.value.id, {
      ext_fields: { ...(archive.value.ext_fields ?? {}), ZY: sumText.value },
    });
    archive.value = { ...archive.value, ext_fields: { ...(archive.value.ext_fields ?? {}), ZY: sumText.value } };
    message.success("已填入「摘要」著录字段");
  } catch {
    message.error("写入失败（正式库档案请在著录页修改）");
  }
}

onUnmounted(stopSumPoll);
onDeactivated(stopSumPoll);

// ── PDF 视图状态 ──────────────────────────────────────────────
const pageCount = ref(0);
const currentPage = ref(1);
const zoom = ref(1);
const rotation = ref(0);
const canvasWrap = ref<HTMLElement | null>(null);
const baseWidth = ref(800);
const infoCollapsed = ref(false);

const activeAttachment = computed(() => attachments.value.find((a) => a.id === activeKey.value) ?? null);
const pdfUrl = computed(() => activeAttachment.value?.url ?? null);
const pageWidth = computed(() => Math.round(baseWidth.value * zoom.value));

// ── 全文提取状态 ──────────────────────────────────────────────
interface PageText { page: number; text: string }
type PdfDocProxy = { numPages: number; getPage: (n: number) => Promise<{ getTextContent: () => Promise<{ items: Array<{ str?: string }> }> }> };

const showText = ref(false);
const extracting = ref(false);
const pageTexts = ref<PageText[]>([]);
const textQuery = ref("");
let pdfDoc: PdfDocProxy | null = null;

// 服务端 OCR 识别全文（Dify OCR 存库结果，优先于前端 PDF 文本层）
const serverText = ref("");
async function loadServerText() {
  if (!archiveId.value) return;
  try {
    const res = await AiAdminAPI.ocrText(archiveId.value);
    serverText.value = res.data.full_text || "";
  } catch {
    serverText.value = "";
  }
}

const hasText = computed(() => !!serverText.value || pageTexts.value.some((p) => p.text.trim().length > 0));
const totalChars = computed(() =>
  serverText.value ? serverText.value.length : pageTexts.value.reduce((s, p) => s + p.text.length, 0),
);
const fullText = computed(() =>
  serverText.value || pageTexts.value.map((p) => p.text).join("\n\n"),
);
const matchCount = computed(() => {
  const q = textQuery.value.trim();
  if (!q) return 0;
  const re = new RegExp(escapeReg(q), "gi");
  return (fullText.value.match(re) ?? []).length;
});

const MJ_LABEL: Record<string, string> = {
  public: "公开", internal: "内部", secret: "秘密", confidential: "机密", top_secret: "绝密",
};
const BGQX_LABEL: Record<string, string> = { permanent: "永久", long: "长期", short: "短期" };

const metaFields = computed(() => {
  const a = archive.value;
  if (!a) return [];
  return [
    { label: "档号", value: a.DH, mono: true },
    { label: "题名", value: a.TM, mono: false },
    { label: "责任者", value: a.RZZ, mono: false },
    { label: "年度", value: a.ND ? `${a.ND} 年` : "", mono: false },
    { label: "文件日期", value: a.WJRQ, mono: false },
    { label: "页数", value: a.YS ? `${a.YS} 页` : "", mono: false },
    { label: "全宗号", value: a.QZH, mono: true },
    { label: "密级", value: MJ_LABEL[a.MJ] ?? a.MJ, mono: false },
    { label: "保管期限", value: BGQX_LABEL[a.BGQX] ?? a.BGQX, mono: false },
  ];
});

const extEntries = computed(() => Object.entries(archive.value?.ext_fields ?? {}));
const attachmentOptions = computed(() => attachments.value.map((a) => ({ label: a.original_name, value: a.id })));

// ── 工具栏动作 ────────────────────────────────────────────────
function zoomIn() { zoom.value = Math.min(zoom.value + 0.2, 3); }
function zoomOut() { zoom.value = Math.max(zoom.value - 0.2, 0.4); }
function resetZoom() { zoom.value = 1; }
function fitWidth() { measure(); zoom.value = 1; }
function rotate() { rotation.value = (rotation.value + 90) % 360; }
async function toggleInfo() { infoCollapsed.value = !infoCollapsed.value; await nextMeasure(); }

function download() {
  if (!pdfUrl.value) return;
  const a = document.createElement("a");
  a.href = pdfUrl.value;
  a.download = activeAttachment.value?.original_name ?? "archive.pdf";
  a.target = "_blank";
  a.click();
}
function openRaw() { if (pdfUrl.value) window.open(pdfUrl.value, "_blank", "noopener"); }
function printPdf() {
  if (!pdfUrl.value) return;
  const frame = document.createElement("iframe");
  frame.style.display = "none";
  frame.src = pdfUrl.value;
  frame.onload = () => {
    try { frame.contentWindow?.focus(); frame.contentWindow?.print(); }
    catch { window.open(pdfUrl.value!, "_blank", "noopener"); }
  };
  document.body.appendChild(frame);
}
function goBack() {
  if (window.history.length > 1) router.back();
  else router.push("/archive/utilization/reading");
}

function onScroll() {
  const el = canvasWrap.value;
  if (!el || pageCount.value <= 1) return;
  const ratio = el.scrollTop / Math.max(1, el.scrollHeight - el.clientHeight);
  currentPage.value = Math.min(pageCount.value, Math.max(1, Math.round(ratio * (pageCount.value - 1)) + 1));
}

// ── PDF 事件 + 全文提取 ───────────────────────────────────────
async function onLoaded(doc: PdfDocProxy) {
  pageCount.value = doc?.numPages ?? 1;
  currentPage.value = 1;
  pdfDoc = doc;
  pageTexts.value = [];
  if (showText.value) await extractText();
}
function onFailed() { message.error("原文加载失败，请稍后重试或下载查看"); }

async function extractText() {
  if (!pdfDoc || pageTexts.value.length > 0) return;
  extracting.value = true;
  try {
    const out: PageText[] = [];
    for (let i = 1; i <= pdfDoc.numPages; i++) {
      const pg = await pdfDoc.getPage(i);
      const tc = await pg.getTextContent();
      const text = tc.items.map((it) => it.str ?? "").join(" ").replace(/[ \t]+/g, " ").trim();
      out.push({ page: i, text });
    }
    pageTexts.value = out;
  } catch {
    message.error("全文提取失败");
  } finally {
    extracting.value = false;
  }
}

async function toggleText() {
  showText.value = !showText.value;
  await nextMeasure();
  if (showText.value) await extractText();
}

async function copyAll() {
  try {
    await navigator.clipboard.writeText(fullText.value);
    message.success("全文已复制到剪贴板");
  } catch {
    message.error("复制失败，请手动选择文本");
  }
}

function escapeHtml(s: string): string {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}
function escapeReg(s: string): string {
  return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}
function highlight(text: string): string {
  const safe = escapeHtml(text);
  const q = textQuery.value.trim();
  if (!q) return safe;
  return safe.replace(new RegExp(`(${escapeReg(escapeHtml(q))})`, "gi"), "<mark>$1</mark>");
}

// ── 尺寸 / 数据 ───────────────────────────────────────────────
function measure() {
  const el = canvasWrap.value;
  if (el) baseWidth.value = Math.max(360, el.clientWidth - 64);
}
async function nextMeasure() {
  await new Promise((r) => requestAnimationFrame(() => r(null)));
  measure();
}

async function load() {
  if (!archiveId.value) { loading.value = false; return; }
  loading.value = true;
  pageTexts.value = [];
  try {
    const [detail, atts] = await Promise.all([
      ArchiveAPI.get(archiveId.value),
      ArchiveAPI.attachments(archiveId.value),
    ]);
    archive.value = detail.data;
    attachments.value = (atts.data ?? []).filter((a) => a.url);
    activeKey.value = attachments.value[0]?.id ?? "";
  } catch {
    message.error("加载档案失败");
  } finally {
    loading.value = false;
  }
}

watch(activeKey, () => { currentPage.value = 1; rotation.value = 0; pageTexts.value = []; pdfDoc = null; });
watch(archiveId, () => {
  sumText.value = "";
  sumStatus.value = "idle";
  serverText.value = "";
  load();
  loadServerText();
  fetchSummary();
});

onMounted(async () => {
  fetchSummary();
  loadServerText();
  await load();
  measure();
  window.addEventListener("resize", measure);
});
</script>

<style scoped>
.pdf-scroll :deep(canvas) {
  box-shadow: 0 2px 14px rgba(0, 0, 0, 0.14);
  background: #fff;
}
.ocr-text :deep(mark) {
  background: oklch(var(--p) / 0.28);
  color: inherit;
  border-radius: 2px;
  padding: 0 1px;
}
</style>
