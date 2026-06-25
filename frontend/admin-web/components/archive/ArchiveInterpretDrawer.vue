<template>
  <NDrawer :show="show" :width="520" placement="right" @update:show="(v: boolean) => emit('update:show', v)">
    <NDrawerContent closable>
      <template #header>
        <div class="flex items-center gap-2">
          <Icon name="heroicons:sparkles" class="w-5 h-5" style="color: oklch(var(--p))" />
          <span>AI 解读</span>
        </div>
      </template>

      <div class="flex flex-col gap-3">
        <div v-if="title" class="text-[13px] pb-2 border-b" style="color: var(--semi-color-text-2); border-color: var(--semi-color-border)">
          {{ title }}
        </div>

        <div v-if="streaming && !text" class="flex items-center gap-2 text-sm py-6" style="color: var(--semi-color-text-3)">
          <NSpin size="small" /> AI 正在阅读该档案全文并解读…
        </div>

        <div
          v-if="text"
          class="markdown-body text-[13.5px] leading-relaxed break-words"
          style="color: var(--semi-color-text-0)"
          v-html="rendered"
        />
        <span
          v-if="streaming && text"
          class="inline-block w-[7px] h-[15px] align-text-bottom animate-pulse"
          style="background: oklch(var(--p)/0.6)"
        />

        <p v-if="error" class="text-sm" style="color: #dc2626">{{ error }}</p>
      </div>

      <template #footer>
        <NButton size="small" :disabled="streaming" @click="rerun">
          <template #icon><Icon name="heroicons:arrow-path" class="w-4 h-4" /></template>
          重新解读
        </NButton>
      </template>
    </NDrawerContent>
  </NDrawer>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { NButton, NDrawer, NDrawerContent, NSpin } from "naive-ui";
import { marked } from "marked";
import DOMPurify from "dompurify";
import { streamInterpret } from "@/api/ai";

marked.setOptions({ gfm: true, breaks: true });

const props = defineProps<{ show: boolean; archiveId: string | null; title?: string }>();
const emit = defineEmits<{ (e: "update:show", v: boolean): void }>();

const text = ref("");

// markdown → 安全 HTML（对 streaming 半截 markdown 容忍）
const rendered = computed(() => {
  if (!text.value) return "";
  let html: string;
  try {
    html = marked.parse(text.value, { async: false }) as string;
  } catch {
    html = text.value.replace(/\n/g, "<br/>");
  }
  return DOMPurify.sanitize(html, { ADD_ATTR: ["target", "rel"] });
});
const streaming = ref(false);
const error = ref("");
let abort: AbortController | null = null;

async function run() {
  if (!props.archiveId) return;
  abort?.abort();
  abort = new AbortController();
  text.value = "";
  error.value = "";
  streaming.value = true;
  try {
    for await (const chunk of streamInterpret(props.archiveId, abort.signal)) {
      if (chunk.event === "error") {
        error.value = chunk.message || "解读失败";
        break;
      }
      if (chunk.answer) text.value += chunk.answer;
    }
    if (!text.value && !error.value) error.value = "未返回解读内容";
  } catch {
    error.value = "请求失败，请确认 AI 服务是否正常";
  } finally {
    streaming.value = false;
  }
}

function rerun() {
  run();
}

watch(
  () => [props.show, props.archiveId] as const,
  ([show]) => {
    if (show && props.archiveId) run();
    else if (!show) abort?.abort();
  },
);
</script>

<style scoped>
.markdown-body :deep(p) { margin: 0.4em 0; }
.markdown-body :deep(p:first-child) { margin-top: 0; }
.markdown-body :deep(p:last-child) { margin-bottom: 0; }
.markdown-body :deep(strong) { color: oklch(var(--p)); font-weight: 600; }
.markdown-body :deep(em) { font-style: italic; }
.markdown-body :deep(ul), .markdown-body :deep(ol) { margin: 0.4em 0; padding-left: 1.4em; }
.markdown-body :deep(li) { margin: 2px 0; }
.markdown-body :deep(ul li::marker) { color: oklch(var(--p)/0.6); }
.markdown-body :deep(h1),
.markdown-body :deep(h2),
.markdown-body :deep(h3),
.markdown-body :deep(h4) { font-weight: 600; margin: 0.6em 0 0.3em; color: var(--semi-color-text-0); }
.markdown-body :deep(h1) { font-size: 15px; }
.markdown-body :deep(h2) { font-size: 14px; }
.markdown-body :deep(h3), .markdown-body :deep(h4) { font-size: 13.5px; }
.markdown-body :deep(code) {
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  background: var(--semi-color-fill-0); padding: 1px 5px; border-radius: 4px;
  font-size: 12px; color: oklch(var(--p));
}
.markdown-body :deep(pre) {
  background: var(--semi-color-fill-0); padding: 10px 12px; border-radius: 8px;
  overflow-x: auto; margin: 0.5em 0; font-size: 12px; line-height: 1.5;
}
.markdown-body :deep(pre code) { background: transparent; padding: 0; color: var(--semi-color-text-0); }
.markdown-body :deep(table) { border-collapse: collapse; margin: 0.5em 0; font-size: 12px; width: 100%; }
.markdown-body :deep(th), .markdown-body :deep(td) {
  border: 1px solid var(--semi-color-border); padding: 4px 8px; text-align: left;
}
.markdown-body :deep(th) { background: var(--semi-color-fill-0); font-weight: 600; }
.markdown-body :deep(blockquote) {
  border-left: 3px solid oklch(var(--p)/0.4); padding-left: 10px; margin: 0.5em 0;
  color: var(--semi-color-text-2);
}
.markdown-body :deep(a) { color: oklch(var(--p)); text-decoration: underline; }
.markdown-body :deep(hr) { border: none; border-top: 1px solid var(--semi-color-border); margin: 0.7em 0; }
</style>
