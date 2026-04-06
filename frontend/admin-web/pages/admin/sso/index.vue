<template>
  <div
    class="bg-[var(--semi-color-bg-0)] rounded-xl border border-[var(--semi-color-border)] shadow-sm p-6 min-h-[500px]"
  >
    <div class="flex justify-between items-center mb-6">
      <h2 class="text-lg font-semibold text-[var(--semi-color-text-0)]">
        SSO 身份源接入
      </h2>
      <Button theme="solid" type="primary"
        ><template #icon><IconPlus /></template>添加身份源</Button
      >
    </div>
    <Table :columns="columns" :data-source="data" empty-text="暂无接入记录" />
  </div>
</template>

<script setup lang="ts">
import { Button, Table } from "@kousum/semi-ui-vue";
import { IconPlus } from "@kousum/semi-icons-vue";

definePageMeta({ layout: "admin", middleware: "auth" });

const columns = [
  { title: "身份源名称", dataIndex: "name" },
  { title: "协议类型", dataIndex: "protocol" }, // e.g. OAuth2, OIDC, SAML
  { title: "Client ID", dataIndex: "clientId" },
  { title: "状态", dataIndex: "status" },
  { title: "操作", dataIndex: "actions" },
];
const data = [];
</script>
