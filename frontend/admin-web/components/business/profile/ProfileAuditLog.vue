<template>
  <div
    class="rounded-2xl border shadow-sm"
    style="background:var(--semi-color-bg-0);border-color:var(--semi-color-border)"
  >
    <div class="px-6 py-4 border-b" style="border-color:var(--semi-color-border)">
      <h2 class="font-semibold" style="color:var(--semi-color-text-0)">操作日志</h2>
      <p class="text-xs mt-0.5" style="color:var(--semi-color-text-2)">您的近期操作记录</p>
    </div>
    <div class="p-6">
      <div v-if="loading && !logs.length" class="flex justify-center py-16">
        <NSpin size="large" />
      </div>
      <NEmpty v-else-if="!logs.length" description="暂无操作记录" class="py-16" />
      <NDataTable
        v-else
        :columns="columns"
        :data="logs"
        :pagination="false"
        size="small"
      />
      <div v-if="hasMore" class="mt-4 flex justify-center">
        <NButton :loading="loading" @click="loadMore">加载更多</NButton>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue";
import { NSpin, NEmpty, NDataTable, NButton, useMessage } from "naive-ui";
import { UserAPI, type AuditLogItem } from "@/api/iam";

const message = useMessage();
const LIMIT = 20;
const logs = ref<AuditLogItem[]>([]);
const loading = ref(false);
const hasMore = ref(false);
const skip = ref(0);

const columns = [
  {
    title: "操作时间",
    key: "created_at",
    width: 160,
    render: (row: AuditLogItem) => new Date(row.create_time).toLocaleString("zh-CN"),
  },
  { title: "操作类型", key: "action" },
  { title: "资源", key: "resource_type" },
  { title: "IP 地址", key: "ip_address" },
];

async function fetchLogs(reset = false) {
  loading.value = true;
  try {
    const res = await UserAPI.getMyAuditLogs({
      skip: reset ? 0 : skip.value,
      limit: LIMIT,
    });
    const data = res.data || [];
    if (reset) {
      logs.value = data;
      skip.value = data.length;
    } else {
      logs.value.push(...data);
      skip.value += data.length;
    }
    hasMore.value = data.length >= LIMIT;
  } catch {
    message.error("加载日志失败");
  } finally {
    loading.value = false;
  }
}

const loadMore = () => fetchLogs(false);

onMounted(() => fetchLogs(true));
</script>
