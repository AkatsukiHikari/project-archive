<template>
  <div class="flex flex-col gap-2">
    <span class="text-[10.5px]" style="color:var(--semi-color-text-3)">
      原文附件（{{ attachments.length }}）
    </span>

    <!-- 拖拽 / 点击上传 -->
    <NUpload
      multiple
      accept=".pdf,.ofd"
      :default-upload="false"
      :show-file-list="false"
      :file-list="[]"
      :disabled="uploading"
      @change="onFilesChange"
    >
      <NUploadDragger>
        <div class="flex items-center justify-center gap-2 py-2.5">
          <Icon name="heroicons:cloud-arrow-up" class="w-5 h-5" style="color:oklch(var(--p))" />
          <span class="text-[12px]" style="color:var(--semi-color-text-2)">
            {{ uploading ? "上传中…" : "拖拽或点击上传 PDF / OFD 原文" }}
          </span>
        </div>
      </NUploadDragger>
    </NUpload>

    <div v-if="loading" class="py-4 text-center text-[12px]" style="color:var(--semi-color-text-3)">
      加载中…
    </div>
    <div
      v-else-if="!attachments.length"
      class="py-3 text-center rounded-lg text-[12px]"
      style="background:var(--semi-color-fill-0);color:var(--semi-color-text-3)"
    >
      尚未挂接数字化成果
    </div>

    <div
      v-for="att in attachments"
      :key="att.id"
      class="flex items-center gap-2 px-3 py-2 rounded-lg"
      style="background:var(--semi-color-fill-0)"
    >
      <Icon
        :name="att.file_format === 'ofd' ? 'heroicons:document' : 'heroicons:document-text'"
        class="w-4 h-4 shrink-0"
        style="color:oklch(var(--p))"
      />
      <div class="flex-1 min-w-0">
        <p class="text-[12px] truncate" style="color:var(--semi-color-text-0)">
          {{ att.original_name }}
          <NTag v-if="att.is_primary" size="tiny" type="success" :bordered="false" class="ml-1">主件</NTag>
        </p>
        <p class="text-[10.5px]" style="color:var(--semi-color-text-3)">
          {{ (att.file_format ?? "").toUpperCase() }}
          <template v-if="att.file_size"> · {{ formatSize(att.file_size) }}</template>
          <template v-if="att.page_count"> · {{ att.page_count }} 页</template>
        </p>
      </div>
      <NButton v-if="att.url" size="tiny" quaternary tag="a" :href="att.url" target="_blank">
        预览
      </NButton>
      <NButton v-if="!att.is_primary" size="tiny" quaternary @click="makePrimary(att)">
        设为主件
      </NButton>
      <NButton size="tiny" quaternary type="error" @click="remove(att)">
        删除
      </NButton>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from "vue";
import { NButton, NTag, NUpload, NUploadDragger, useDialog, useMessage } from "naive-ui";
import type { UploadFileInfo } from "naive-ui";
import { ArchiveAPI, OrganizeAPI } from "@/api/repository";
import type { ArchiveAttachment } from "@/api/repository";

const props = defineProps<{ archiveId: string }>();
const emit = defineEmits<{ changed: [] }>();

const message = useMessage();
const dialog = useDialog();
const attachments = ref<ArchiveAttachment[]>([]);
const loading = ref(false);
const uploading = ref(false);

async function load() {
  loading.value = true;
  try {
    const res = await ArchiveAPI.attachments(props.archiveId);
    attachments.value = res.data ?? [];
  } finally {
    loading.value = false;
  }
}

async function onFilesChange({ fileList }: { fileList: UploadFileInfo[] }) {
  const picked = fileList.map((f) => f.file).filter((f): f is File => !!f);
  if (!picked.length || uploading.value) return;
  uploading.value = true;
  try {
    let ok = 0;
    for (const file of picked) {
      const res = await OrganizeAPI.uploadAttachment(
        props.archiveId, file, attachments.value.length === 0 && ok === 0,
      );
      if (res.code === 0) ok += 1;
      else message.error(`${file.name}：${res.message}`);
    }
    if (ok) {
      message.success(`已挂接 ${ok} 个原文`);
      await load();
      emit("changed");
    }
  } finally {
    uploading.value = false;
  }
}

async function makePrimary(att: ArchiveAttachment) {
  const res = await OrganizeAPI.setPrimaryAttachment(att.id);
  if (res.code === 0) {
    message.success("已设为主件");
    await load();
  } else {
    message.error(res.message);
  }
}

function remove(att: ArchiveAttachment) {
  dialog.warning({
    title: "删除附件",
    content: `确认删除「${att.original_name}」？`,
    positiveText: "删除",
    negativeText: "取消",
    onPositiveClick: async () => {
      const res = await OrganizeAPI.deleteAttachment(att.id);
      if (res.code === 0) {
        message.success("已删除");
        await load();
        emit("changed");
      } else {
        message.error(res.message);
      }
    },
  });
}

function formatSize(bytes: number): string {
  if (bytes >= 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
  return `${Math.max(1, Math.round(bytes / 1024))} KB`;
}

watch(() => props.archiveId, load);
onMounted(load);
</script>
