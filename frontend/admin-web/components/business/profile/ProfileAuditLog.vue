<template>
  <div
    class="rounded-2xl bg-[var(--semi-color-bg-0)] border border-[var(--semi-color-border)] shadow-sm"
  >
    <div class="px-6 py-4 border-b border-[var(--semi-color-border)]">
      <h2 class="font-semibold text-[var(--semi-color-text-0)]">操作日志</h2>
      <p class="text-xs text-[var(--semi-color-text-2)] mt-0.5">
        您的近期操作记录
      </p>
    </div>
    <div class="p-6">
      <div v-if="loading && !logs.length" class="flex justify-center py-16">
        <Spin size="large" />
      </div>
      <Empty
        v-else-if="!logs.length"
        description="暂无操作记录"
        class="py-16"
      />
      <Table
        v-else
        :columns="columns"
        :data-source="logs"
        :pagination="false"
        size="small"
        empty-text="暂无日志"
      />
      <div v-if="hasMore" class="mt-4 flex justify-center">
        <Button :loading="loading" @click="loadMore">加载更多</Button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue";
import { Spin, Empty, Table, Button, Toast } from "@kousum/semi-ui-vue";
import { UserAPI, type AuditLogItem } from "@/api/iam";

const LIMIT = 20;
const logs = ref<AuditLogItem[]>([]);
const loading = ref(false);
const hasMore = ref(false);
const skip = ref(0);

const columns = [
  {
    title: "操作时间",
    dataIndex: "created_at",
    width: 160,
    render: (v: string) => new Date(v).toLocaleString("zh-CN"),
  },
  { title: "操作类型", dataIndex: "action" },
  { title: "资源", dataIndex: "resource_type" },
  { title: "IP 地址", dataIndex: "ip_address" },
];

async function fetch(reset = false) {
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
    Toast.error("加载日志失败");
  } finally {
    loading.value = false;
  }
}

const loadMore = () => fetch(false);

onMounted(() => fetch(true));
</script>
