<template>
  <div v-if="show" class="fixed inset-0 z-[1000] bg-white flex flex-col">
    <!-- 顶部 -->
    <div class="h-14 shrink-0 border-b border-gray-200 flex items-center gap-3 px-4">
      <Icon name="heroicons:document-duplicate" class="w-5 h-5 text-indigo-600 shrink-0" />
      <NInput v-model:value="name" :disabled="readonly" placeholder="模板名称" size="small" style="width: 240px" />
      <NSelect v-model:value="resultType" :options="typeOptions" :disabled="readonly" size="small" style="width: 150px" />
      <NInput v-model:value="description" :disabled="readonly" placeholder="模板说明（可选）" size="small" class="flex-1" />
      <NTag v-if="readonly" type="info" size="small" round>内置模板（只读）</NTag>
      <NButton v-if="!readonly" size="small" type="primary" :loading="saving" @click="save">保存</NButton>
      <NButton size="small" quaternary @click="close">
        <template #icon><Icon name="heroicons:x-mark" class="w-5 h-5" /></template>
      </NButton>
    </div>
    <!-- 编辑器 -->
    <div class="flex-1 min-h-0">
      <ClientOnly>
        <UmoEditor v-if="ready" ref="editorRef" v-bind="options" />
      </ClientOnly>
    </div>
  </div>
</template>

<script setup lang="ts">
import { nextTick, reactive, ref, watch } from "vue";
import { NButton, NInput, NSelect, NTag, useMessage } from "naive-ui";
import {
  RESULT_TYPES, ResearchTemplateAPI, ResearchUploadAPI, type ResultType,
} from "@/api/research";

const props = defineProps<{ show: boolean; templateId: string | null }>();
const emit = defineEmits<{
  (e: "update:show", v: boolean): void;
  (e: "saved"): void;
}>();

const message = useMessage();
const typeOptions = RESULT_TYPES.map((t) => ({ label: t, value: t }));

const name = ref("");
const resultType = ref<ResultType>("专题汇编");
const description = ref("");
const readonly = ref(false);
const ready = ref(false);
const saving = ref(false);

const editorRef = ref<{ getHTML: () => string; getJSON: () => Record<string, unknown>; setReadOnly?: (v: boolean) => void } | null>(null);
const options = reactive<Record<string, unknown>>({});

function buildOptions(content: string) {
  Object.assign(options, {
    document: { title: name.value || "编研模板", content: content || "<p></p>" },
    toolbar: { defaultMode: "ribbon", menus: ["base", "insert", "table", "tools", "page", "export"] },
    async onFileUpload(file: File) {
      const res = await ResearchUploadAPI.upload(file);
      return { id: res.data.id, url: res.data.url };
    },
  });
}

watch(
  () => [props.show, props.templateId] as const,
  async ([show, id]) => {
    if (!show) {
      ready.value = false;
      return;
    }
    ready.value = false;
    if (id) {
      const res = await ResearchTemplateAPI.get(id);
      const t = res.data;
      name.value = t.name;
      resultType.value = t.result_type;
      description.value = t.description || "";
      readonly.value = t.is_builtin;
      buildOptions(t.content || "");
    } else {
      name.value = "";
      resultType.value = "专题汇编";
      description.value = "";
      readonly.value = false;
      buildOptions("<p></p>");
    }
    ready.value = true;
    await nextTick();
    if (readonly.value) editorRef.value?.setReadOnly?.(true);
  },
  { immediate: true },
);

async function save() {
  if (!name.value.trim()) return message.warning("请填写模板名称");
  if (!editorRef.value) return;
  saving.value = true;
  try {
    const payload = {
      name: name.value.trim(),
      result_type: resultType.value,
      description: description.value || null,
      content: editorRef.value.getHTML(),
      content_json: editorRef.value.getJSON(),
    };
    const res = props.templateId
      ? await ResearchTemplateAPI.update(props.templateId, payload)
      : await ResearchTemplateAPI.create(payload);
    if (res.code === 0) {
      message.success("已保存");
      emit("saved");
      close();
    } else {
      message.error(res.message);
    }
  } finally {
    saving.value = false;
  }
}

function close() {
  emit("update:show", false);
}
</script>
