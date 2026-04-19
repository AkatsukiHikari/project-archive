<template>
  <div
    class="rounded-xl border p-6 min-h-[500px]"
    style="background:var(--semi-color-bg-0);border-color:var(--semi-color-border)"
  >
    <div class="flex justify-between items-center mb-6">
      <h2 class="text-lg font-semibold" style="color:var(--semi-color-text-0)">SSO 身份源接入</h2>
      <NButton type="primary" disabled>
        <template #icon><Icon name="heroicons:plus" class="w-4 h-4" /></template>
        添加身份源
      </NButton>
    </div>
    <NDataTable :columns="columns" :data="data" :pagination="false">
      <template #empty><NEmpty description="暂无接入记录" class="py-10" /></template>
    </NDataTable>
  </div>
</template>

<script setup lang="ts">
import { NButton, NDataTable, NEmpty } from "naive-ui";

definePageMeta({ layout: "admin", middleware: "auth" });

const columns = [
  { title: "身份源名称", key: "name" },
  { title: "协议类型", key: "protocol" },
  { title: "Client ID", key: "clientId" },
  { title: "状态", key: "status" },
  { title: "操作", key: "actions" },
];
const data: never[] = [];
</script>
