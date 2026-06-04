<template>
  <div class="flex flex-col gap-4 h-full overflow-auto">
    <!-- 头部 -->
    <div class="flex items-center justify-between flex-shrink-0">
      <div class="flex items-center gap-2.5">
        <div class="w-8 h-8 rounded-xl flex items-center justify-center" style="background:oklch(var(--p)/0.12)">
          <Icon name="heroicons:book-open" class="w-4 h-4" style="color:oklch(var(--p))" />
        </div>
        <div>
          <h1 class="text-[15px] font-semibold leading-tight" style="color:var(--semi-color-text-0)">AI 知识库管理</h1>
          <p class="text-[11px] leading-tight" style="color:var(--semi-color-text-3)">
            L1 元数据 · L4 业务规则 · L2 原文 OCR
          </p>
        </div>
      </div>
      <NButton text size="small" @click="reload" :loading="loading">
        <template #icon><Icon name="heroicons:arrow-path" class="w-3.5 h-3.5" /></template>
        刷新
      </NButton>
    </div>

    <!-- 三张 KB 状态卡 -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-3 flex-shrink-0">
      <div
        v-for="item in items"
        :key="item.kb_type"
        class="rounded-xl p-4 flex flex-col gap-3 transition-all"
        :style="{
          background: 'var(--semi-color-bg-0)',
          border: '1px solid var(--semi-color-border)',
          boxShadow: item.synced ? '0 0 0 1px oklch(var(--su)/0.18) inset' : '0 0 0 1px oklch(0.65 0.18 80/0.18) inset',
        }"
      >
        <div class="flex items-start justify-between gap-3">
          <div class="flex items-center gap-2">
            <div
              class="w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0"
              :style="{ background: kbColor(item.kb_type) + '/0.14', color: kbColor(item.kb_type) }"
            >
              <Icon :name="kbIcon(item.kb_type)" class="w-4 h-4" />
            </div>
            <div>
              <div class="text-[13px] font-semibold leading-tight" style="color:var(--semi-color-text-0)">
                {{ kbLabel(item.kb_type) }}
              </div>
              <div class="text-[11px] leading-tight mt-0.5" style="color:var(--semi-color-text-3)">
                {{ kbSubtitle(item.kb_type) }}
              </div>
            </div>
          </div>
          <NTag
            size="small"
            :type="item.synced ? 'success' : 'warning'"
            :bordered="false"
          >
            {{ item.synced ? '已同步' : '需同步' }}
          </NTag>
        </div>

        <div class="grid grid-cols-2 gap-2 text-[12px]">
          <div class="rounded-md px-2.5 py-2" style="background:var(--semi-color-fill-0)">
            <div class="text-[10.5px]" style="color:var(--semi-color-text-3)">数据库</div>
            <div class="text-[15px] font-semibold tabular-nums" style="color:var(--semi-color-text-0)">
              {{ item.db_count.toLocaleString() }}
            </div>
          </div>
          <div class="rounded-md px-2.5 py-2" style="background:var(--semi-color-fill-0)">
            <div class="text-[10.5px]" style="color:var(--semi-color-text-3)">索引</div>
            <div class="text-[15px] font-semibold tabular-nums" style="color:var(--semi-color-text-0)">
              {{ item.es_count == null ? '—' : item.es_count.toLocaleString() }}
            </div>
          </div>
        </div>

        <div v-if="item.note" class="text-[11px] leading-relaxed" style="color:var(--semi-color-text-2)">
          {{ item.note }}
        </div>
        <div v-if="item.last_synced_at" class="text-[10.5px]" style="color:var(--semi-color-text-3)">
          最近同步：{{ item.last_synced_at }}
        </div>

        <div class="mt-auto">
          <NButton
            v-if="item.kb_type === 'meta'"
            block
            size="small"
            :type="item.synced ? 'default' : 'primary'"
            :loading="rebuilding === item.kb_type"
            :disabled="rebuilding !== null"
            @click="onRebuild(item.kb_type)"
          >
            <template #icon><Icon name="heroicons:arrow-path" class="w-3.5 h-3.5" /></template>
            {{ item.synced ? '强制重建' : '立即同步' }}
          </NButton>
          <NButton v-else block size="small" disabled>
            {{ item.kb_type === 'rules' ? 'L4 规则由 seed 脚本管理' : 'P3 OCR 阶段上线' }}
          </NButton>
        </div>
      </div>
    </div>

    <!-- 上次重建结果（如果有） -->
    <div
      v-if="lastResult"
      class="rounded-xl p-4"
      style="background:var(--semi-color-bg-0);border:1px solid var(--semi-color-border)"
    >
      <div class="flex items-center gap-2 mb-2">
        <Icon name="heroicons:check-circle" class="w-4 h-4" style="color:oklch(var(--su))" />
        <span class="text-[13px] font-semibold" style="color:var(--semi-color-text-0)">最近一次重建</span>
      </div>
      <div class="grid grid-cols-2 md:grid-cols-4 gap-2 text-[12px]">
        <div>
          <div class="text-[10.5px]" style="color:var(--semi-color-text-3)">KB</div>
          <div class="font-medium" style="color:var(--semi-color-text-0)">{{ lastResult.kb_type }}</div>
        </div>
        <div>
          <div class="text-[10.5px]" style="color:var(--semi-color-text-3)">扫描</div>
          <div class="font-medium tabular-nums">{{ lastResult.scanned }}</div>
        </div>
        <div>
          <div class="text-[10.5px]" style="color:var(--semi-color-text-3)">成功</div>
          <div class="font-medium tabular-nums" style="color:oklch(var(--su))">{{ lastResult.synced }}</div>
        </div>
        <div>
          <div class="text-[10.5px]" style="color:var(--semi-color-text-3)">失败 · 耗时</div>
          <div class="font-medium tabular-nums">
            <span :style="lastResult.failed > 0 ? 'color:oklch(var(--er))' : ''">{{ lastResult.failed }}</span>
            · {{ lastResult.duration_ms }} ms
          </div>
        </div>
      </div>
    </div>

    <!-- 提示 -->
    <div
      class="rounded-xl p-4 flex gap-3"
      style="background:oklch(var(--in)/0.06);border:1px solid oklch(var(--in)/0.25)"
    >
      <Icon name="heroicons:information-circle" class="w-4 h-4 mt-0.5 shrink-0" style="color:oklch(var(--in))" />
      <div class="text-[12px] leading-relaxed" style="color:var(--semi-color-text-1)">
        <div class="font-semibold mb-1" style="color:var(--semi-color-text-0)">关于知识库</div>
        <div>
          AI 问答和检索完全依赖知识库索引。<strong>L1 元数据</strong>来自档案库，新增 / 修改 / 删除档案时通过增量同步实时入索引；
          若发现索引与数据库不一致，可点击"强制重建"全量推一遍。
          <strong>L4 业务规则</strong>来自 30 条种子（DA/T 标准 + 内部规章），由 <code class="px-1 rounded" style="background:var(--semi-color-fill-0)">seed_ai_rules.py</code> 维护。
          <strong>L2 OCR</strong> 暂未启用，P3 阶段接入扫描件全文检索。
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue";
import { NButton, NTag, useMessage } from "naive-ui";
import {
  getKBStatus,
  rebuildKB,
  type KBRebuildResponse,
  type KBStatusItem,
} from "@/api/ai";

definePageMeta({
  layout: "portal",
  middleware: "auth",
  breadcrumb: [
    { name: "AI 档案助手", path: "/ai" },
    { name: "知识库管理", path: "/ai/knowledge" },
  ],
});

const message = useMessage();

const items = ref<KBStatusItem[]>([]);
const loading = ref(false);
const rebuilding = ref<string | null>(null);
const lastResult = ref<KBRebuildResponse | null>(null);

const kbLabel = (t: string): string => ({
  meta: "L1 档案元数据",
  rules: "L4 业务规则",
  ocr: "L2 原文 OCR",
}[t] ?? t);

const kbSubtitle = (t: string): string => ({
  meta: "档号 / 题名 / 责任者 / 密级 等核心字段",
  rules: "DA/T 标准 / 保管期限 / 内部规章",
  ocr: "扫描件全文（P3 阶段接入）",
}[t] ?? "");

const kbIcon = (t: string): string => ({
  meta: "heroicons:rectangle-stack",
  rules: "heroicons:book-open",
  ocr: "heroicons:photo",
}[t] ?? "heroicons:cube");

const kbColor = (t: string): string => ({
  meta: "oklch(var(--p))",
  rules: "oklch(0.55 0.2 290)",
  ocr: "oklch(0.55 0.16 200)",
}[t] ?? "oklch(var(--p))");

const reload = async () => {
  loading.value = true;
  try {
    const res = await getKBStatus();
    items.value = res.items;
  } catch (e: any) {
    message.error(e?.message ?? "加载知识库状态失败");
  } finally {
    loading.value = false;
  }
};

const onRebuild = async (kbType: "meta") => {
  rebuilding.value = kbType;
  try {
    const res = await rebuildKB(kbType, 500);
    lastResult.value = res;
    message.success(`重建完成：扫描 ${res.scanned} / 成功 ${res.synced} / 失败 ${res.failed}`);
    await reload();
  } catch (e: any) {
    message.error(e?.message ?? "重建失败");
  } finally {
    rebuilding.value = null;
  }
};

onMounted(() => reload());
</script>
