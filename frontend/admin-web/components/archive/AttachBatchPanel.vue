<template>
  <div class="flex flex-col gap-4">
    <!-- 拖拽上传区 -->
    <NUpload
      multiple
      directory-dnd
      accept=".pdf,.ofd"
      :default-upload="false"
      :show-file-list="false"
      :file-list="[]"
      @change="onFilesChange"
    >
      <NUploadDragger>
        <div class="flex flex-col items-center gap-2 py-6">
          <Icon name="heroicons:cloud-arrow-up" class="w-10 h-10" style="color:oklch(var(--p))" />
          <p class="text-[14px] font-medium" style="color:var(--semi-color-text-0)">
            点击或拖拽 PDF / OFD 文件到此处
          </p>
          <p class="text-[12px]" style="color:var(--semi-color-text-3)">
            文件名（去扩展名）须与档号一致，如 <code class="font-mono">J001-WS-2025-0001.pdf</code>，支持一次多选
          </p>
        </div>
      </NUploadDragger>
    </NUpload>

    <!-- 预检结果 -->
    <template v-if="preview && !result">
      <div class="grid grid-cols-3 gap-3">
        <div class="rounded-lg p-3 text-center" style="background:oklch(var(--su)/0.08)">
          <p class="text-[22px] font-bold m-0" style="color:oklch(var(--su))">{{ preview.matched }}</p>
          <p class="text-[12px] m-0" style="color:var(--semi-color-text-2)">可挂接</p>
        </div>
        <div class="rounded-lg p-3 text-center" style="background:oklch(0.65 0.15 80/0.1)">
          <p class="text-[22px] font-bold m-0" style="color:oklch(0.6 0.18 80)">{{ preview.has_primary }}</p>
          <p class="text-[12px] m-0" style="color:var(--semi-color-text-2)">已有原文</p>
        </div>
        <div class="rounded-lg p-3 text-center" style="background:oklch(var(--er)/0.08)">
          <p class="text-[22px] font-bold m-0" style="color:oklch(var(--er))">{{ preview.not_found }}</p>
          <p class="text-[12px] m-0" style="color:var(--semi-color-text-2)">无此档号</p>
        </div>
      </div>

      <ProTable :columns="previewColumns" :data="preview.rows" :page-size="0" size="small" max-height="300" />

      <div class="flex items-center gap-3">
        <label class="flex items-center gap-1.5 text-[12.5px] cursor-pointer" style="color:var(--semi-color-text-1)">
          <NSwitch v-model:value="overwrite" size="small" />
          覆盖已有原文（{{ preview.has_primary }} 件）
        </label>
        <div class="flex-1" />
        <NButton tertiary @click="resetAll">重选文件</NButton>
        <NButton type="primary" :disabled="attachableCount === 0" :loading="attaching" @click="execute">
          <template #icon><Icon name="heroicons:paper-clip" class="w-4 h-4" /></template>
          开始挂接（{{ attachableCount }} 件）
        </NButton>
      </div>
    </template>

    <!-- 执行结果报表 -->
    <template v-if="result">
      <div
        class="rounded-lg p-4 flex items-center gap-4"
        :style="result.not_found || result.skipped
          ? 'background:oklch(0.65 0.15 80/0.1)'
          : 'background:oklch(var(--su)/0.08)'"
      >
        <Icon
          :name="result.not_found || result.skipped ? 'heroicons:exclamation-triangle' : 'heroicons:check-circle'"
          class="w-8 h-8 shrink-0"
          :style="result.not_found || result.skipped ? 'color:oklch(0.6 0.18 80)' : 'color:oklch(var(--su))'"
        />
        <div>
          <p class="text-[14px] font-semibold m-0" style="color:var(--semi-color-text-0)">
            挂接批次 {{ result.batch_no }} 完成
          </p>
          <p class="text-[12.5px] m-0 mt-0.5" style="color:var(--semi-color-text-2)">
            成功 <b style="color:oklch(var(--su))">{{ result.attached }}</b> 件
            · 跳过 {{ result.skipped }} 件 · 无匹配 {{ result.not_found }} 件
            · 明细已留痕，可在「挂接历史」中追溯
          </p>
        </div>
        <div class="flex-1" />
        <NButton size="small" @click="resetAll">继续挂接</NButton>
      </div>
      <ProTable :columns="resultColumns" :data="result.rows" :page-size="0" size="small" max-height="300" />
    </template>
  </div>
</template>

<script setup lang="tsx">
import { computed, h, ref } from "vue";
import { NButton, NSwitch, NTag, NUpload, NUploadDragger, useMessage } from "naive-ui";
import type { DataTableColumns, UploadFileInfo } from "naive-ui";
import { ProTable } from "@/components/ui";
import { OrganizeAPI } from "@/api/repository";
import type { AttachBatchResult, AttachMatchRow, AttachPreviewResult } from "@/api/repository";

const emit = defineEmits<{ done: [AttachBatchResult] }>();

const message = useMessage();
const files = ref<File[]>([]);
const overwrite = ref(false);
const preview = ref<AttachPreviewResult | null>(null);
const result = ref<AttachBatchResult | null>(null);
const attaching = ref(false);

const attachableCount = computed(() => {
  if (!preview.value) return 0;
  return preview.value.matched + (overwrite.value ? preview.value.has_primary : 0);
});

async function onFilesChange({ fileList }: { fileList: UploadFileInfo[] }) {
  const picked = fileList.map((f) => f.file).filter((f): f is File => !!f);
  if (!picked.length) return;
  files.value = picked;
  result.value = null;
  const res = await OrganizeAPI.attachPreview(picked.map((f) => f.name));
  if (res.code === 0) preview.value = res.data;
  else message.error(res.message);
}

async function execute() {
  attaching.value = true;
  try {
    const res = await OrganizeAPI.attachBatch(files.value, overwrite.value);
    if (res.code === 0) {
      result.value = res.data;
      preview.value = null;
      emit("done", res.data);
    } else {
      message.error(res.message);
    }
  } finally {
    attaching.value = false;
  }
}

function resetAll() {
  files.value = [];
  preview.value = null;
  result.value = null;
  overwrite.value = false;
}

defineExpose({ resetAll });

const STATUS_TAG: Record<string, { label: string; type: "success" | "warning" | "error" | "info" | "default" }> = {
  matched: { label: "可挂接", type: "success" },
  has_primary: { label: "已有原文", type: "warning" },
  not_found: { label: "无此档号", type: "error" },
  attached: { label: "已挂接", type: "success" },
  skipped: { label: "已跳过", type: "warning" },
};

function statusCell(row: AttachMatchRow) {
  const meta = STATUS_TAG[row.status] ?? { label: row.status, type: "default" as const };
  return h(NTag, { size: "small", type: meta.type, round: true, bordered: false }, { default: () => meta.label });
}

const baseColumns: DataTableColumns<AttachMatchRow> = [
  { title: "文件名", key: "filename", minWidth: 200, ellipsis: { tooltip: true } },
  { title: "档号", key: "DH", width: 190, ellipsis: { tooltip: true } },
  { title: "匹配档案", key: "TM", minWidth: 160, ellipsis: { tooltip: true }, render: (r) => r.TM ?? "—" },
  {
    title: "库", key: "source", width: 70,
    render: (r) => (r.source === "formal" ? "正式库" : r.source === "staging" ? "暂存库" : "—"),
  },
];

const previewColumns: DataTableColumns<AttachMatchRow> = [
  ...baseColumns,
  { title: "预检", key: "status", width: 100, render: statusCell },
];
const resultColumns: DataTableColumns<AttachMatchRow> = [
  ...baseColumns,
  { title: "结果", key: "status", width: 100, render: statusCell },
  { title: "说明", key: "reason", width: 150, render: (r) => r.reason ?? "—" },
];
</script>
