<template>
  <div class="flex flex-col gap-4">
    <AdminPageHeader
      title="批量导入"
      description="通过 CSV / Excel 文件批量导入档案条目，支持字段映射与预检"
      icon="heroicons:arrow-up-tray"
    />

    <!-- 步骤条 -->
    <div class="pro-card p-5">
      <NSteps :current="step" size="small">
        <NStep title="上传文件" description="选择 CSV 或 Excel 文件" />
        <NStep title="字段映射" description="将文件列与档案字段对应" />
        <NStep title="预检验证" description="检查数据合规性" />
        <NStep title="执行导入" description="触发异步导入任务" />
        <NStep title="导入完成" description="查看结果报告" />
        <NStep title="挂接成果" description="按档号批量挂接数字化成果" />
      </NSteps>
    </div>

    <!-- Step 1: 上传文件 -->
    <div v-if="step === 1" class="pro-card p-5 flex flex-col gap-5">
      <div class="grid grid-cols-3 gap-4">
        <div class="flex flex-col gap-1">
          <span class="text-sm font-medium">全宗 <span class="text-red-500">*</span></span>
          <NSelect
            v-model:value="meta.fonds_id"
            :options="fondsOptions"
            placeholder="选择全宗"
            @update:value="onFondsChange"
          />
        </div>
        <div class="flex flex-col gap-1">
          <span class="text-sm font-medium">目录 <span class="text-red-500">*</span></span>
          <NSelect
            v-model:value="meta.catalog_id"
            :options="catalogOptions"
            placeholder="选择目录"
            :disabled="!meta.fonds_id"
          />
        </div>
        <div class="flex flex-col gap-1">
          <span class="text-sm font-medium">门类 <span class="text-red-500">*</span></span>
          <NSelect v-model:value="meta.category_id" :options="categoryOptions" placeholder="选择门类" />
        </div>
      </div>

      <NUpload
        :max="1"
        accept=".csv,.xlsx,.xls"
        :custom-request="handleUpload"
        :show-file-list="true"
        :disabled="uploading"
        @before-upload="beforeUpload"
      >
        <NUploadDragger>
          <div class="flex flex-col items-center gap-3 py-8">
            <Icon name="heroicons:arrow-up-tray" class="w-10 h-10 text-gray-400" />
            <p class="text-base">点击或拖拽文件到此处上传</p>
            <p class="text-sm text-gray-400">支持 .csv / .xlsx / .xls，单次最大 10 MB</p>
          </div>
        </NUploadDragger>
      </NUpload>

      <div v-if="uploading" class="flex items-center gap-2 text-sm text-blue-600">
        <NSpin size="small" />
        <span>正在上传并解析文件…</span>
      </div>
    </div>

    <!-- Step 2: 字段映射 -->
    <div v-if="step === 2" class="pro-card p-5 flex flex-col gap-4">
      <div class="flex items-center justify-between">
        <p class="text-sm text-gray-500">
          识别到 <strong>{{ uploadResult?.columns.length }}</strong> 列，请将每列映射到档案字段（无需映射的列选"忽略"）
        </p>
        <NSelect
          v-model:value="selectedTemplate"
          :options="templateOptions"
          placeholder="从模板加载映射"
          style="width: 220px"
          clearable
          @update:value="applyTemplate"
        />
      </div>

      <ProTable
        :columns="mappingColumns"
        :data="mappings"
        :page-size="0"
        size="small"
      />

      <div class="flex items-center gap-3 mt-2">
        <NCheckbox v-model:checked="saveTemplate">保存为映射模板</NCheckbox>
        <NInput
          v-if="saveTemplate"
          v-model:value="templateName"
          placeholder="模板名称"
          style="width: 200px"
        />
      </div>

      <div class="flex justify-between">
        <NButton @click="step = 1">上一步</NButton>
        <NButton type="primary" :loading="mappingSaving" @click="submitMapping">下一步（预检）</NButton>
      </div>
    </div>

    <!-- Step 3: 预检结果 -->
    <div v-if="step === 3" class="pro-card p-5 flex flex-col gap-4">
      <div class="grid grid-cols-4 gap-4">
        <div class="rounded-lg border p-4 text-center">
          <p class="text-2xl font-bold">{{ dryRunResult?.total ?? 0 }}</p>
          <p class="text-sm text-gray-500 mt-1">总行数</p>
        </div>
        <div class="rounded-lg border border-green-200 bg-green-50 p-4 text-center">
          <p class="text-2xl font-bold text-green-600">{{ dryRunResult?.ok ?? 0 }}</p>
          <p class="text-sm text-gray-500 mt-1">可导入</p>
        </div>
        <div class="rounded-lg border border-yellow-200 bg-yellow-50 p-4 text-center">
          <p class="text-2xl font-bold text-yellow-600">{{ dryRunResult?.warning ?? 0 }}</p>
          <p class="text-sm text-gray-500 mt-1">警告</p>
        </div>
        <div class="rounded-lg border border-red-200 bg-red-50 p-4 text-center">
          <p class="text-2xl font-bold text-red-600">{{ dryRunResult?.error ?? 0 }}</p>
          <p class="text-sm text-gray-500 mt-1">错误</p>
        </div>
      </div>

      <div v-if="dryRunResult && dryRunResult.rows?.length > 0">
        <p class="text-sm font-medium mb-2">行检验明细（最多显示 50 条）</p>
        <ProTable
          :columns="dryRunColumns"
          :data="dryRunResult.rows"
          :page-size="0"
          size="small"
          max-height="300"
        />
      </div>

      <div class="flex justify-between">
        <NButton @click="step = 2">上一步</NButton>
        <NButton
          type="primary"
          :disabled="(dryRunResult?.error ?? 0) > 0"
          @click="executeImport"
        >
          {{ (dryRunResult?.error ?? 0) > 0 ? '存在错误，无法导入' : '开始导入' }}
        </NButton>
      </div>
    </div>

    <!-- Step 4: 执行中 -->
    <div v-if="step === 4" class="pro-card p-5 flex flex-col items-center gap-6 py-10">
      <NSpin :size="48" />
      <p class="text-base font-medium">正在导入，请稍候…</p>
      <div class="w-full max-w-md">
        <NProgress
          type="line"
          :percentage="progress.percent"
          :status="progress.failed > 0 ? 'warning' : 'default'"
          indicator-placement="inside"
          processing
        />
        <p class="text-sm text-gray-500 mt-2 text-center">
          已处理 {{ progress.processed }} / {{ progress.total }} 条
          （成功 {{ progress.success }}，失败 {{ progress.failed }}）
        </p>
      </div>
    </div>

    <!-- Step 5: 完成 -->
    <div v-if="step === 5" class="pro-card p-5 flex flex-col items-center gap-6 py-10">
      <Icon name="heroicons:check-circle" class="w-16 h-16 text-green-500" />
      <p class="text-xl font-semibold">导入完成</p>
      <div class="grid grid-cols-3 gap-6 text-center">
        <div>
          <p class="text-2xl font-bold text-green-600">{{ finalTask?.success ?? 0 }}</p>
          <p class="text-sm text-gray-500">成功</p>
        </div>
        <div>
          <p class="text-2xl font-bold text-red-500">{{ finalTask?.failed ?? 0 }}</p>
          <p class="text-sm text-gray-500">失败</p>
        </div>
        <div>
          <p class="text-2xl font-bold text-gray-400">{{ finalTask?.skipped ?? 0 }}</p>
          <p class="text-sm text-gray-500">跳过</p>
        </div>
      </div>
      <div class="flex gap-3">
        <NButton v-if="reportUrl" tag="a" :href="reportUrl" target="_blank" type="warning">
          <template #icon><Icon name="heroicons:arrow-down-tray" class="w-4 h-4" /></template>
          下载失败报表
        </NButton>
        <NButton type="primary" @click="step = 6">
          <template #icon><Icon name="heroicons:paper-clip" class="w-4 h-4" /></template>
          挂接数字化成果
        </NButton>
        <NButton tertiary @click="restart">再次导入</NButton>
      </div>
    </div>

    <!-- Step 6: 挂接数字化成果 -->
    <div v-if="step === 6" class="pro-card p-5 flex flex-col gap-4">
      <p class="text-sm m-0" style="color:var(--semi-color-text-2)">
        刚导入的著录条目已生成档号，把对应的数字化成果（PDF / OFD，文件名 = 档号）拖入下方即可批量挂接。
        每次挂接自动留痕，可在 档案整理 → 挂接成果 → 挂接历史 中追溯。
      </p>
      <AttachBatchPanel @done="attachDone = true" />
      <div class="flex justify-between">
        <NButton @click="step = 5">上一步</NButton>
        <NButton :type="attachDone ? 'primary' : 'default'" @click="restart">
          {{ attachDone ? "完成，再次导入" : "跳过，再次导入" }}
        </NButton>
      </div>
    </div>
  </div>
</template>

<script setup lang="tsx">
import { ref, computed, onMounted, onUnmounted, reactive } from "vue";
import {
  NSteps, NStep, NSelect, NUpload, NUploadDragger, NSpin, NProgress,
  NButton, NCheckbox, NInput, NTag, useMessage,
} from "naive-ui";
import type { DataTableColumns, UploadCustomRequestOptions } from "naive-ui";
import { FondsAPI, CatalogAPI, CategoryAPI } from "@/api/repository";
import type { Fonds, Catalog, ArchiveCategory } from "@/api/repository";
import { ImportAPI } from "@/api/collection";
import type { UploadResponse, DryRunResponse, ImportTask, ColumnMapping, MappingTemplate } from "@/api/collection";
import { AdminPageHeader } from "@/components/admin";
import { ProTable } from "@/components/ui";
import { AttachBatchPanel } from "@/components/archive";
import { useUserStore } from "@/stores/user";

definePageMeta({ layout: "archive", middleware: "auth" });

const message = useMessage();
const userStore = useUserStore();

const step = ref(1);
const attachDone = ref(false);

const fondsList = ref<Fonds[]>([]);
const catalogList = ref<Catalog[]>([]);
const categoryList = ref<ArchiveCategory[]>([]);

const fondsOptions = computed(() =>
  fondsList.value.map((f) => ({ label: `${f.fonds_code} - ${f.name}`, value: f.id })),
);
const catalogOptions = computed(() =>
  catalogList.value.map((c) => ({ label: `${c.catalog_no} ${c.name}`, value: c.id })),
);
const categoryOptions = computed(() =>
  categoryList.value.map((c) => ({ label: `${c.code} - ${c.name}`, value: c.id })),
);

async function onFondsChange(id: string | null) {
  meta.catalog_id = null;
  catalogList.value = [];
  if (id) {
    const res = await CatalogAPI.list(id);
    catalogList.value = res.data;
  }
}

const meta = reactive({
  fonds_id: null as string | null,
  catalog_id: null as string | null,
  category_id: null as string | null,
});

const uploading = ref(false);
const uploadResult = ref<UploadResponse | null>(null);
const taskId = ref<string | null>(null);

function beforeUpload() {
  if (!meta.fonds_id || !meta.catalog_id || !meta.category_id) {
    message.warning("请先选择全宗、目录和门类");
    return false;
  }
  return true;
}

async function handleUpload({ file, onFinish, onError }: UploadCustomRequestOptions) {
  uploading.value = true;
  try {
    const res = await ImportAPI.upload(
      file.file as File,
      meta.category_id!,
      meta.fonds_id!,
      meta.catalog_id!,
    );
    const data = res.data;
    uploadResult.value = data;
    taskId.value = data.task_id;

    mappings.value = data.columns.map((col) => {
      const auto = data.auto_mappings?.find((m: ColumnMapping) => m.source_col === col);
      return { source_col: col, target_field: auto?.target_field ?? null };
    });

    const tplRes = await ImportAPI.listTemplates(meta.category_id!);
    templates.value = tplRes.data;

    onFinish();
    step.value = 2;
  } catch {
    onError();
  } finally {
    uploading.value = false;
  }
}

const mappings = ref<ColumnMapping[]>([]);
const templates = ref<MappingTemplate[]>([]);
const selectedTemplate = ref<string | null>(null);
const saveTemplate = ref(false);
const templateName = ref("");
const mappingSaving = ref(false);

const templateOptions = computed(() =>
  templates.value.map((t) => ({ label: t.name, value: t.id })),
);

const archiveFieldOptions = [
  { label: "忽略", value: null },
  { label: "题名", value: "title" },
  { label: "责任者", value: "creator" },
  { label: "年度", value: "year" },
  { label: "档号", value: "archive_no" },
  { label: "全宗号", value: "fonds_code" },
  { label: "案卷号", value: "volume_no" },
  { label: "件号", value: "item_no" },
  { label: "目录号", value: "catalog_no" },
  { label: "文件日期", value: "doc_date" },
  { label: "页数", value: "pages" },
  { label: "密级", value: "security_level" },
  { label: "保管期限", value: "retention_period" },
];

const mappingColumns: DataTableColumns<ColumnMapping> = [
  { title: "文件列头", key: "source_col", width: 200 },
  {
    title: "映射到档案字段",
    key: "target_field",
    render: (row, idx) => (
      <NSelect
        value={row.target_field}
        options={archiveFieldOptions as any}
        size="small"
        style="width: 200px"
        onUpdateValue={(v: string | null) => { mappings.value[idx].target_field = v; }}
      />
    ),
  },
];

function applyTemplate(id: string | null) {
  if (!id) return;
  const tpl = templates.value.find((t) => t.id === id);
  if (!tpl) return;
  mappings.value = mappings.value.map((m) => {
    const match = tpl.mappings.find((tm) => tm.source_col === m.source_col);
    return match ? { ...m, target_field: match.target_field } : m;
  });
  message.success("已应用模板映射");
}

async function submitMapping() {
  mappingSaving.value = true;
  try {
    await ImportAPI.saveMapping(
      taskId.value!,
      mappings.value,
      saveTemplate.value,
      saveTemplate.value ? templateName.value : undefined,
    );
    const res = await ImportAPI.dryRun(taskId.value!);
    dryRunResult.value = res.data as any;
    step.value = 3;
  } finally {
    mappingSaving.value = false;
  }
}

const dryRunResult = ref<DryRunResponse | null>(null);

const dryRunStatusOptions = [
  { label: "正常", value: "ok" },
  { label: "警告", value: "warning" },
  { label: "错误", value: "error" },
];

const dryRunColumns = [
  { title: "行号", key: "row", width: 80 },
  {
    title: "状态",
    key: "status",
    width: 90,
    search: { type: "select" as const, options: dryRunStatusOptions },
    render: (row: any) => {
      const typeMap: Record<string, "default" | "warning" | "error"> = {
        ok: "default", warning: "warning", error: "error",
      };
      return <NTag type={typeMap[row.status] ?? "default"} size="small">{row.status}</NTag>;
    },
  },
  { title: "说明", key: "message", ellipsis: { tooltip: true }, search: { placeholder: "请输入说明" } },
];

const progress = reactive({ processed: 0, total: 0, success: 0, failed: 0, percent: 0 });
const finalTask = ref<ImportTask | null>(null);
const reportUrl = ref<string | null>(null);
let ws: WebSocket | null = null;

async function executeImport() {
  step.value = 4;
  Object.assign(progress, {
    processed: 0,
    total: dryRunResult.value?.total ?? 0,
    success: 0,
    failed: 0,
    percent: 0,
  });
  await ImportAPI.execute(taskId.value!);
  connectProgressWs(taskId.value!);
}

function connectProgressWs(tid: string) {
  const token = userStore.token;
  const host = window.location.host;
  const proto = window.location.protocol === "https:" ? "wss" : "ws";
  ws = new WebSocket(`${proto}://${host}/ws/import/${tid}?token=${token}`);

  ws.onmessage = (event) => {
    try {
      const msg = JSON.parse(event.data);
      if (msg.type === "progress") {
        progress.processed = msg.processed ?? 0;
        progress.total = msg.total ?? progress.total;
        progress.success = msg.success ?? 0;
        progress.failed = msg.failed ?? 0;
        progress.percent = progress.total > 0
          ? Math.round((progress.processed / progress.total) * 100)
          : 0;
      } else if (msg.type === "done" || msg.type === "failed") {
        ws?.close();
        step.value = 5;
        loadFinalTask(tid);
      }
    } catch {
      // ignore parse errors
    }
  };

  ws.onerror = () => pollTaskStatus(tid);
}

async function pollTaskStatus(tid: string) {
  const interval = setInterval(async () => {
    try {
      const res = await ImportAPI.getTask(tid);
      const task = res.data;
      if (task.status === "done" || task.status === "failed") {
        clearInterval(interval);
        finalTask.value = task;
        step.value = 5;
        if (task.failed > 0) {
          const rRes = await ImportAPI.getReport(tid);
          reportUrl.value = rRes.data.url;
        }
      }
    } catch {
      clearInterval(interval);
    }
  }, 3000);
}

async function loadFinalTask(tid: string) {
  try {
    const res = await ImportAPI.getTask(tid);
    finalTask.value = res.data;
    if (finalTask.value?.failed && finalTask.value.failed > 0) {
      const rRes = await ImportAPI.getReport(tid);
      reportUrl.value = rRes.data.url;
    }
  } catch {
    // ignore
  }
}

function restart() {
  step.value = 1;
  attachDone.value = false;
  uploadResult.value = null;
  taskId.value = null;
  dryRunResult.value = null;
  finalTask.value = null;
  reportUrl.value = null;
  mappings.value = [];
  Object.assign(progress, { processed: 0, total: 0, success: 0, failed: 0, percent: 0 });
}

async function loadRefData() {
  const [fondsRes, catRes] = await Promise.all([FondsAPI.list(), CategoryAPI.list()]);
  fondsList.value = fondsRes.data;
  categoryList.value = catRes.data;
}

onMounted(loadRefData);
onUnmounted(() => ws?.close());
</script>
