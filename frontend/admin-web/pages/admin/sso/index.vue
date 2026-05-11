<template>
  <div class="flex flex-col gap-4">
    <AdminPageHeader
      title="SSO 身份源接入"
      description="配置第三方身份提供者（SAML 2.0 / OIDC / CAS），实现单点登录"
      icon="heroicons:key"
    />
    <ProTable :columns="columns" :data="data" empty-content="暂无接入记录">
      <template #toolbar-right>
        <NButton type="primary" disabled>
          <template #icon><Icon name="heroicons:plus" class="w-4 h-4" /></template>
          添加身份源
        </NButton>
      </template>
    </ProTable>
  </div>
</template>

<script setup lang="ts">
import { NButton } from "naive-ui";
import { AdminPageHeader } from "@/components/admin";
import { ProTable } from "@/components/ui";

definePageMeta({ layout: "admin", middleware: "auth" });

const statusOptions = [
  { label: "已启用", value: "active" },
  { label: "已禁用", value: "disabled" },
];

const columns = [
  { title: "身份源名称", key: "name", search: { placeholder: "请输入名称" } },
  { title: "协议类型", key: "protocol", search: { placeholder: "请输入协议" } },
  { title: "Client ID", key: "clientId" },
  {
    title: "状态", key: "status",
    search: { type: "select" as const, options: statusOptions },
  },
  { title: "操作", key: "actions" },
];
const data: never[] = [];
</script>
