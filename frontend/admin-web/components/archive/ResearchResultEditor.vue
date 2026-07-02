<template>
  <div v-if="show" class="fixed inset-0 z-[1000] flex flex-col" style="background: var(--semi-color-bg-0)">
    <!-- 顶部操作栏 -->
    <div class="h-14 shrink-0 border-b flex items-center gap-2 px-4" style="border-color: var(--semi-color-border)">
      <Icon name="heroicons:document-text" class="w-5 h-5 shrink-0" style="color: oklch(var(--p))" />
      <span class="font-medium truncate max-w-[240px]">{{ result?.title || "编研成果" }}</span>
      <ResultStatusTag v-if="result" :status="result.status" />
      <div class="flex-1" />

      <template v-if="!locked">
        <!-- Gmail 式 AI 起草：图标 → 面板输入 → 生成 → 预览 → 插入光标处 -->
        <NPopover v-model:show="aiShow" trigger="click" placement="bottom-end" :width="580" :show-arrow="false">
          <template #trigger>
            <NButton size="small" type="primary">
              <template #icon><Icon name="heroicons:sparkles" class="w-4 h-4" /></template>
              AI 起草
            </NButton>
          </template>

          <div class="flex flex-col gap-2.5 py-1">
            <!-- 输入 -->
            <template v-if="aiPhase === 'input'">
              <div class="text-[13px] font-semibold" style="color: var(--semi-color-text-0)">想写什么？</div>
              <NInput
                v-model:value="aiTopic"
                type="textarea"
                :autosize="{ minRows: 4, maxRows: 8 }"
                placeholder="描述你想写的大概内容，例如：&#10;围绕 2023 年防汛工作，梳理各阶段部署、行动与成效，突出重点事件。&#10;（留空则按成果体裁基于档案库自动起草）"
              />
              <div class="flex items-center justify-end gap-2">
                <NButton size="small" quaternary @click="aiShow = false">取消</NButton>
                <NButton size="small" type="primary" :loading="aiLoading" @click="aiGenerate">
                  <template #icon><Icon name="heroicons:sparkles" class="w-4 h-4" /></template>
                  作成
                </NButton>
              </div>
            </template>

            <!-- 生成中 -->
            <template v-else-if="aiPhase === 'loading'">
              <div class="flex items-center gap-2 py-8 justify-center text-[13px]" style="color: var(--semi-color-text-2)">
                <NSpin size="small" /> AI 正在依据成果档案库的原文撰写…
              </div>
            </template>

            <!-- 预览 -->
            <template v-else>
              <div class="flex items-center gap-2">
                <span class="text-[13px] font-semibold" style="color: var(--semi-color-text-0)">AI 草稿预览</span>
                <span v-if="aiSummary" class="text-[11px] truncate" style="color: var(--semi-color-text-3)">{{ aiSummary }}</span>
              </div>
              <!-- eslint-disable-next-line vue/no-v-html -->
              <div class="ai-preview max-h-[46vh] overflow-auto rounded-lg border p-3 text-[13px] leading-relaxed" style="border-color: var(--semi-color-border)" v-html="aiContent" />
              <div class="flex items-center gap-2">
                <NButton size="small" quaternary @click="aiPhase = 'input'">
                  <template #icon><Icon name="heroicons:arrow-left" class="w-3.5 h-3.5" /></template>
                  重新输入
                </NButton>
                <NButton size="small" tertiary :loading="aiLoading" @click="aiGenerate">重新生成</NButton>
                <div class="flex-1" />
                <NButton size="small" type="primary" @click="aiInsert">
                  <template #icon><Icon name="heroicons:arrow-down-on-square" class="w-4 h-4" /></template>
                  插入
                </NButton>
              </div>
            </template>
          </div>
        </NPopover>
        <NButton v-if="result?.result_type === '大事记'" size="small" tertiary :loading="chronLoading" @click="insertChronicle">
          大事记表格
        </NButton>
        <NButton size="small" tertiary @click="insertReferences">引用目录</NButton>
      </template>

      <NButton size="small" tertiary @click="showLib = !showLib">
        <template #icon><Icon name="heroicons:rectangle-stack" class="w-4 h-4" /></template>
        档案库 {{ archives.length }}
      </NButton>
      <NDivider vertical />
      <NButton v-if="!locked" size="small" type="primary" :loading="saving" @click="save">保存</NButton>
      <NButton
        v-for="b in workflowBtns"
        :key="b.action"
        size="small"
        tertiary
        :type="b.type"
        @click="doTransition(b.action, b.label)"
      >
        {{ b.label }}
      </NButton>
      <NButton size="small" quaternary @click="close">
        <template #icon><Icon name="heroicons:x-mark" class="w-5 h-5" /></template>
      </NButton>
    </div>

    <!-- 主体：编辑器 + 档案库面板 -->
    <div class="flex-1 min-h-0 flex">
      <div class="flex-1 min-w-0 h-full">
        <ClientOnly>
          <UmoEditor v-if="ready" ref="editorRef" v-bind="options" @saved="onEditorSaved" />
        </ClientOnly>
      </div>

      <div v-show="showLib" class="w-96 shrink-0 border-l flex flex-col" style="border-color: var(--semi-color-border); background: var(--semi-color-bg-1)">
        <div class="p-3 border-b flex items-center justify-between" style="border-color: var(--semi-color-border)">
          <span class="text-sm font-medium" style="color: var(--semi-color-text-0)">成果档案库</span>
          <span class="text-xs" style="color: var(--semi-color-text-3)">{{ archives.length }} 件</span>
        </div>
        <div class="p-3 flex gap-2 border-b" style="border-color: var(--semi-color-border)">
          <NButton size="small" type="primary" tertiary class="flex-1" :disabled="locked" @click="openPicker">
            <template #icon><Icon name="heroicons:plus" class="w-4 h-4" /></template>
            从馆藏选档
          </NButton>
          <NButton v-if="result?.project_id" size="small" tertiary class="flex-1" :disabled="locked" :loading="importing" @click="importProject">
            <template #icon><Icon name="heroicons:arrow-down-on-square" class="w-4 h-4" /></template>
            导入项目素材
          </NButton>
        </div>
        <p class="px-3 pt-2 text-[11px]" style="color: var(--semi-color-text-3)">点「查看原文」对照 PDF / OCR 全文撰写，点「引用」在正文光标处插入档案引用。</p>
        <div class="flex-1 overflow-y-auto p-3 flex flex-col gap-2">
          <div
            v-for="a in archives"
            :key="a.id"
            class="rounded-lg border p-2.5 text-xs transition-colors"
            :style="{
              background: 'var(--semi-color-bg-0)',
              borderColor: a.archive_id === viewerArchiveId ? 'oklch(var(--p))' : 'var(--semi-color-border)',
              boxShadow: a.archive_id === viewerArchiveId ? '0 0 0 1px oklch(var(--p)/0.35)' : 'none',
            }"
          >
            <div class="font-medium line-clamp-2 leading-snug" style="color: var(--semi-color-text-0)">{{ a.TM }}</div>
            <div class="mt-1 truncate" style="color: var(--semi-color-text-3)">{{ a.DH || "无档号" }} · {{ a.WJRQ || a.ND || "" }}{{ a.RZZ ? " · " + a.RZZ : "" }}</div>
            <div class="flex items-center gap-1 mt-2">
              <NButton size="tiny" tertiary @click="openViewer(a)">
                <template #icon><Icon name="heroicons:document-magnifying-glass" class="w-3.5 h-3.5" /></template>
                查看原文
              </NButton>
              <NButton size="tiny" type="primary" tertiary :disabled="locked" @click="insertCite(a)">插入引用</NButton>
              <div class="flex-1" />
              <NButton size="tiny" quaternary type="error" :disabled="locked" @click="removeArchive(a.id)">
                <template #icon><Icon name="heroicons:trash" class="w-3.5 h-3.5" /></template>
              </NButton>
            </div>
          </div>
          <div v-if="!archives.length" class="text-center text-xs py-8 px-2" style="color: var(--semi-color-text-3)">
            尚未建立档案库。<br>编研写作以档案原文为依据——请「从馆藏选档」或「导入项目素材」，再对照原文撰写。
          </div>
        </div>
      </div>
    </div>

    <!-- 选档弹窗 -->
    <ArchivePickerModal
      ref="pickerRef"
      v-model:show="pickerShow"
      :exclude-ids="archiveIds"
      :z-index="1100"
      @confirm="onPick"
      @view="openViewerById"
    />

    <!-- 原文查看器 -->
    <NDrawer v-model:show="viewerShow" :width="viewerWidth" placement="right" :z-index="1100">
      <NDrawerContent :native-scrollbar="false" :body-content-style="{ padding: 0, height: '100%' }" closable>
        <template #header>档案原文</template>
        <ArchiveSourceViewer
          :archive-id="viewerArchiveId"
          :title="viewerTitle"
          :dh="viewerDh"
          @insert-cite="insertCiteCurrent"
        />
      </NDrawerContent>
    </NDrawer>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, reactive, ref, watch } from "vue";
import { NButton, NDivider, NDrawer, NDrawerContent, NInput, NPopover, NSpin, useMessage } from "naive-ui";
import { ArchivePickerModal, ArchiveSourceViewer, ResultStatusTag } from "@/components/archive";
import {
  ResearchResultAPI, ResearchUploadAPI,
  type ResearchResult, type ResultAction, type ResultArchive,
} from "@/api/research";

const props = defineProps<{ show: boolean; resultId: string | null }>();
const emit = defineEmits<{
  (e: "update:show", v: boolean): void;
  (e: "saved"): void;
}>();

const message = useMessage();

const result = ref<ResearchResult | null>(null);
const archives = ref<ResultArchive[]>([]);
const ready = ref(false);
const showLib = ref(true);
const saving = ref(false);
const importing = ref(false);
const aiLoading = ref(false);
const chronLoading = ref(false);
const aiTopic = ref("");

interface TiptapEditor {
  chain: () => { focus: () => { insertContent: (c: string) => { run: () => void } } };
}
const editorRef = ref<{
  getHTML: () => string;
  getJSON: () => Record<string, unknown>;
  insertContent: (c: string) => void;
  getEditor?: () => { value?: TiptapEditor } | TiptapEditor;
  useEditor?: () => TiptapEditor;
  setReadOnly?: (v: boolean) => void;
} | null>(null);

const locked = computed(
  () => result.value?.status === "finalized" || result.value?.status === "published",
);
const archiveIds = computed(() => archives.value.map((a) => a.archive_id));

const options = reactive<Record<string, unknown>>({});

function buildOptions(r: ResearchResult) {
  Object.assign(options, {
    document: { title: r.title, content: r.content || "<p></p>" },
    toolbar: { defaultMode: "ribbon", menus: ["base", "insert", "table", "tools", "page", "export"] },
    page: { showBreakMarks: true },
    async onFileUpload(file: File) {
      const res = await ResearchUploadAPI.upload(file);
      return { id: res.data.id, url: res.data.url };
    },
    async onSave() {
      await persist();
      return true;
    },
  });
}

watch(
  () => [props.show, props.resultId] as const,
  async ([show, id]) => {
    if (show && id) {
      await load(id);
    } else if (!show) {
      ready.value = false;
      result.value = null;
      viewerShow.value = false;
    }
  },
  { immediate: true },
);

async function load(id: string) {
  ready.value = false;
  const [r, a] = await Promise.all([
    ResearchResultAPI.get(id),
    ResearchResultAPI.listArchives(id),
  ]);
  result.value = r.data;
  archives.value = a.data;
  buildOptions(r.data);
  ready.value = true;
  await nextTick();
  if (locked.value) editorRef.value?.setReadOnly?.(true);
}

async function reloadArchives() {
  if (!props.resultId) return;
  const res = await ResearchResultAPI.listArchives(props.resultId);
  archives.value = res.data;
}

// ── 插入（统一走 tiptap 实例，保证 HTML 被解析渲染）─────────────────────────────
// UmoEditor：useEditor() 直接返回 tiptap 实例；getEditor() 返回 ref（取 .value）。
function tiptapEditor(): TiptapEditor | undefined {
  const r = editorRef.value;
  if (!r) return undefined;
  const direct = r.useEditor?.();
  if (direct?.chain) return direct;
  const got = r.getEditor?.() as { value?: TiptapEditor } | TiptapEditor | undefined;
  if (got && "chain" in got && typeof got.chain === "function") return got as TiptapEditor;
  const inner = (got as { value?: TiptapEditor } | undefined)?.value;
  if (inner?.chain) return inner;
  return undefined;
}

function tiptapInsert(content: string) {
  const ed = tiptapEditor();
  if (ed) ed.chain().focus().insertContent(content).run();
  else editorRef.value?.insertContent?.(content);
}

function citeMarker(a: ResultArchive): string {
  return `〔${a.DH || a.TM}〕`;
}

function insertCite(a: ResultArchive) {
  if (locked.value) return;
  tiptapInsert(citeMarker(a));
}

function insertReferences() {
  if (!archives.value.length) return message.warning("成果档案库为空");
  const items = archives.value
    .map((a) => `<li>${esc(a.TM)}．${esc(a.DH || "")}${a.RZZ ? "．" + esc(a.RZZ) : ""}${a.WJRQ || a.ND ? "．" + esc(String(a.WJRQ || a.ND)) : ""}</li>`)
    .join("");
  tiptapInsert(`<h2>引用档案目录</h2><ol>${items}</ol>`);
  message.success("已插入引用档案目录");
}

async function insertChronicle() {
  if (!props.resultId) return;
  chronLoading.value = true;
  try {
    const res = await ResearchResultAPI.chronicleTable(props.resultId);
    tiptapInsert(res.data.html);
    message.success("已插入大事记表格");
  } finally {
    chronLoading.value = false;
  }
}

// ── Gmail 式 AI 起草：输入 → 作成 → 预览 → 插入光标处 ─────────────────────────
const aiShow = ref(false);
const aiPhase = ref<"input" | "loading" | "preview">("input");
const aiContent = ref("");
const aiSummary = ref("");

async function aiGenerate() {
  if (!props.resultId) return;
  aiLoading.value = true;
  aiPhase.value = "loading";
  try {
    const res = await ResearchResultAPI.aiDraft({
      result_id: props.resultId,
      topic: aiTopic.value.trim() || undefined,
    });
    aiContent.value = res.data.content;
    aiSummary.value = res.data.summary ?? "";
    aiPhase.value = "preview";
  } catch {
    message.error("AI 起草失败，请稍后重试");
    aiPhase.value = "input";
  } finally {
    aiLoading.value = false;
  }
}

function aiInsert() {
  if (!aiContent.value) return;
  tiptapInsert(aiContent.value);
  message.success("已插入光标位置，请核对润色");
  aiShow.value = false;
  aiPhase.value = "input";
}

function esc(s: string): string {
  return s.replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c] as string));
}

// ── 持久化 ────────────────────────────────────────────────────────────────────
async function persist() {
  if (!props.resultId || !editorRef.value) return;
  await ResearchResultAPI.update(props.resultId, {
    content: editorRef.value.getHTML(),
    content_json: editorRef.value.getJSON(),
  });
  emit("saved");
}

async function save() {
  saving.value = true;
  try {
    await persist();
    message.success("已保存");
  } finally {
    saving.value = false;
  }
}

function onEditorSaved() {
  message.success("已保存");
}

// ── 档案库管理 ────────────────────────────────────────────────────────────────
const pickerRef = ref<{ reset: () => void } | null>(null);
const pickerShow = ref(false);

function openPicker() {
  pickerShow.value = true;
  nextTick(() => pickerRef.value?.reset());
}

async function onPick(ids: string[]) {
  if (!props.resultId) return;
  try {
    const res = await ResearchResultAPI.addArchives(props.resultId, { archive_ids: ids });
    if (res.code !== 0) return message.error(res.message || "加入失败");
    pickerShow.value = false;
    await reloadArchives();
    message.success(`已加入 ${res.data.added} 件档案`);
  } catch {
    message.error("加入失败，请重试");
  }
}

async function importProject() {
  if (!props.resultId) return;
  importing.value = true;
  try {
    const res = await ResearchResultAPI.addArchives(props.resultId, { from_project: true });
    if (res.code !== 0) return message.error(res.message || "导入失败");
    await reloadArchives();
    message.success(
      res.data.added > 0
        ? `已从所属项目导入 ${res.data.added} 件档案`
        : "所属项目的素材已全部在档案库中",
    );
  } finally {
    importing.value = false;
  }
}

async function removeArchive(raId: string) {
  await ResearchResultAPI.removeArchive(raId);
  await reloadArchives();
}

// ── 原文查看器 ────────────────────────────────────────────────────────────────
const viewerShow = ref(false);
const viewerArchiveId = ref<string | null>(null);
const viewerTitle = ref("");
const viewerDh = ref("");
const viewerWidth = computed(() => Math.round((typeof window !== "undefined" ? window.innerWidth : 1280) * 0.66));

function openViewer(a: ResultArchive) {
  openViewerById({ archive_id: a.archive_id, TM: a.TM, DH: a.DH || "" });
}

function openViewerById(a: { archive_id: string; TM: string; DH: string }) {
  viewerArchiveId.value = a.archive_id;
  viewerTitle.value = a.TM;
  viewerDh.value = a.DH;
  viewerShow.value = true;
}

function insertCiteCurrent() {
  if (locked.value) return;
  tiptapInsert(`〔${viewerDh.value || viewerTitle.value}〕`);
}

// ── 工作流 ────────────────────────────────────────────────────────────────────
const workflowBtns = computed<{ label: string; action: ResultAction; type: "primary" | "warning" }[]>(() => {
  const s = result.value?.status;
  if (s === "draft") return [{ label: "提交审核", action: "submit", type: "primary" }];
  if (s === "reviewing") return [{ label: "定稿", action: "finalize", type: "primary" }];
  if (s === "finalized") return [
    { label: "发布", action: "publish", type: "primary" },
    { label: "撤回", action: "reopen", type: "warning" },
  ];
  if (s === "published") return [{ label: "撤回", action: "reopen", type: "warning" }];
  return [];
});

async function doTransition(action: ResultAction, label: string) {
  if (!props.resultId) return;
  if (!locked.value) await persist().catch(() => undefined);
  const res = await ResearchResultAPI.transition(props.resultId, action);
  if (res.code === 0) {
    result.value = res.data;
    message.success(`${label}成功`);
    emit("saved");
    await nextTick();
    editorRef.value?.setReadOnly?.(locked.value);
  } else {
    message.error(res.message);
  }
}

function close() {
  emit("update:show", false);
}
</script>

<style scoped>
/* AI 草稿预览：标题/表格/列表基本排版 */
.ai-preview :deep(h2) { font-size: 15px; font-weight: 600; margin: 0.6em 0 0.3em; }
.ai-preview :deep(h3) { font-size: 14px; font-weight: 600; margin: 0.5em 0 0.25em; }
.ai-preview :deep(p) { margin: 0.4em 0; }
.ai-preview :deep(ul), .ai-preview :deep(ol) { margin: 0.4em 0; padding-left: 1.4em; }
.ai-preview :deep(table) { border-collapse: collapse; width: 100%; margin: 0.5em 0; font-size: 12px; }
.ai-preview :deep(th), .ai-preview :deep(td) { border: 1px solid var(--semi-color-border); padding: 4px 8px; text-align: left; }
.ai-preview :deep(th) { background: var(--semi-color-fill-0); font-weight: 600; }
</style>
