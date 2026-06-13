<template>
  <div class="flex flex-col gap-4">
    <AdminPageHeader
      title="鉴定标准"
      description="开放鉴定依据的标准条款与敏感词库，AI 预鉴定按此判定"
      icon="heroicons:scale"
    />

    <div class="pro-card">
      <NTabs v-model:value="tab" type="line" class="px-5 pt-2">
        <!-- ── 标准条款 ── -->
        <NTabPane name="standards" tab="标准条款">
          <div class="flex items-center gap-3 pb-3">
            <NButton tertiary size="small" @click="loadStandards">
              <template #icon><Icon name="heroicons:arrow-path" class="w-4 h-4" /></template>
              刷新
            </NButton>
            <div class="flex-1" />
            <NButton type="primary" size="small" @click="openStandardEdit()">
              <template #icon><Icon name="heroicons:plus" class="w-4 h-4" /></template>
              新增条款
            </NButton>
          </div>
          <ProTable :columns="standardColumns" :data="standards" :loading="standardsLoading" :page-size="10" size="small" />
        </NTabPane>

        <!-- ── 敏感词库 ── -->
        <NTabPane name="words" tab="敏感词库">
          <div class="flex items-center gap-3 pb-3">
            <NInput
              v-model:value="wordKeyword"
              placeholder="搜索敏感词"
              size="small"
              clearable
              style="width: 200px"
              @keyup.enter="loadWords"
              @clear="loadWords"
            />
            <NButton tertiary size="small" @click="loadWords">
              <template #icon><Icon name="heroicons:arrow-path" class="w-4 h-4" /></template>
              刷新
            </NButton>
            <div class="flex-1" />
            <NButton type="primary" size="small" @click="openWordEdit()">
              <template #icon><Icon name="heroicons:plus" class="w-4 h-4" /></template>
              新增敏感词
            </NButton>
          </div>
          <ProTable :columns="wordColumns" :data="words" :loading="wordsLoading" :page-size="15" size="small" />
        </NTabPane>
      </NTabs>
    </div>

    <!-- 条款编辑 -->
    <NModal
      v-model:show="showStandardEdit"
      preset="card"
      :title="standardForm.id ? '编辑标准条款' : '新增标准条款'"
      style="width: 620px; max-width: 95vw"
    >
      <div class="flex flex-col gap-4">
        <div class="grid grid-cols-2 gap-4">
          <div class="flex flex-col gap-1">
            <span class="text-sm font-medium">条款编码 <span class="text-red-500">*</span></span>
            <NInput v-model:value="standardForm.code" placeholder="如 KZ-08" :disabled="!!standardForm.id" />
          </div>
          <div class="flex flex-col gap-1">
            <span class="text-sm font-medium">导向结论 <span class="text-red-500">*</span></span>
            <NSelect v-model:value="standardForm.target_kfzt" :options="kfztOptions" />
          </div>
        </div>
        <div class="flex flex-col gap-1">
          <span class="text-sm font-medium">条款名称 <span class="text-red-500">*</span></span>
          <NInput v-model:value="standardForm.title" placeholder="条款简称" />
        </div>
        <div class="flex flex-col gap-1">
          <span class="text-sm font-medium">条款内容 <span class="text-red-500">*</span></span>
          <NInput v-model:value="standardForm.content" type="textarea" :rows="3" placeholder="结论理由会引用此内容" />
        </div>
        <div class="grid grid-cols-2 gap-4">
          <div class="flex flex-col gap-1">
            <span class="text-sm font-medium">出处</span>
            <NInput v-model:value="standardForm.source" placeholder="如《国家档案馆档案开放办法》第十二条" />
          </div>
          <div class="flex flex-col gap-1">
            <span class="text-sm font-medium">匹配关键词（逗号分隔）</span>
            <NInput v-model:value="standardKeywords" placeholder="命中即建议该条款结论，可空" />
          </div>
        </div>
      </div>
      <template #footer>
        <div class="flex justify-end gap-3">
          <NButton @click="showStandardEdit = false">取消</NButton>
          <NButton type="primary" :loading="saving" @click="saveStandard">保存</NButton>
        </div>
      </template>
    </NModal>

    <!-- 敏感词编辑 -->
    <NModal
      v-model:show="showWordEdit"
      preset="card"
      :title="wordForm.id ? '编辑敏感词' : '新增敏感词'"
      style="width: 480px; max-width: 95vw"
    >
      <div class="flex flex-col gap-4">
        <div class="flex flex-col gap-1">
          <span class="text-sm font-medium">敏感词 <span class="text-red-500">*</span></span>
          <NInput v-model:value="wordForm.word" placeholder="如：商业秘密" />
        </div>
        <div class="grid grid-cols-2 gap-4">
          <div class="flex flex-col gap-1">
            <span class="text-sm font-medium">类别</span>
            <NInput v-model:value="wordForm.category" placeholder="如：个人隐私" />
          </div>
          <div class="flex flex-col gap-1">
            <span class="text-sm font-medium">命中建议结论</span>
            <NSelect v-model:value="wordForm.suggest_kfzt" :options="suggestOptions" />
          </div>
        </div>
      </div>
      <template #footer>
        <div class="flex justify-end gap-3">
          <NButton @click="showWordEdit = false">取消</NButton>
          <NButton type="primary" :loading="saving" @click="saveWord">保存</NButton>
        </div>
      </template>
    </NModal>
  </div>
</template>

<script setup lang="tsx">
import { h, onMounted, reactive, ref } from "vue";
import { NButton, NInput, NModal, NSelect, NSwitch, NTabPane, NTabs, NTooltip, useDialog, useMessage } from "naive-ui";
import type { DataTableColumns } from "naive-ui";
import { AdminPageHeader } from "@/components/admin";
import { ProTable } from "@/components/ui";
import { KfztTag } from "@/components/archive";
import { AppraisalStandardAPI } from "@/api/appraisal";
import type { AppraisalStandard, Kfzt, SensitiveWord } from "@/api/appraisal";

definePageMeta({ layout: "archive", middleware: "auth" });

const message = useMessage();
const dialog = useDialog();
const tab = ref("standards");
const saving = ref(false);

const kfztOptions = (["开放", "控制使用", "延期开放", "不开放"] as Kfzt[]).map((v) => ({ label: v, value: v }));
const suggestOptions = (["控制使用", "延期开放", "不开放"] as Kfzt[]).map((v) => ({ label: v, value: v }));

// ── 标准条款 ──────────────────────────────────────────────────────────────────
const standards = ref<AppraisalStandard[]>([]);
const standardsLoading = ref(false);

async function loadStandards() {
  standardsLoading.value = true;
  try {
    const res = await AppraisalStandardAPI.list();
    standards.value = res.data ?? [];
  } finally {
    standardsLoading.value = false;
  }
}

const standardColumns: DataTableColumns<AppraisalStandard> = [
  { title: "编码", key: "code", width: 80 },
  { title: "条款名称", key: "title", width: 200, ellipsis: { tooltip: true } },
  {
    title: "条款内容", key: "content", minWidth: 260,
    render: (r) => h(NTooltip, null, {
      trigger: () => h("span", { class: "text-xs text-gray-600 line-clamp-1" }, r.content),
      default: () => r.content,
    }),
  },
  { title: "导向结论", key: "target_kfzt", width: 95, render: (r) => h(KfztTag, { value: r.target_kfzt }) },
  {
    title: "关键词", key: "keywords", width: 160,
    render: (r) => h("span", { class: "text-xs text-gray-500" }, r.keywords?.join("、") ?? "—"),
  },
  {
    title: "启用", key: "is_enabled", width: 70,
    render: (r) => h(NSwitch, {
      value: r.is_enabled,
      size: "small",
      onUpdateValue: (v: boolean) => toggleStandard(r, v),
    }),
  },
  {
    title: "操作", key: "actions", width: 110,
    render: (r) => [
      h(NButton, { size: "tiny", tertiary: true, class: "mr-1", onClick: () => openStandardEdit(r) }, { default: () => "编辑" }),
      h(NButton, { size: "tiny", tertiary: true, type: "error", onClick: () => removeStandard(r) }, { default: () => "删除" }),
    ],
  },
];

const showStandardEdit = ref(false);
const standardKeywords = ref("");
const standardForm = reactive({
  id: "" as string,
  code: "",
  title: "",
  content: "",
  target_kfzt: "控制使用" as Kfzt,
  source: "",
});

function openStandardEdit(row?: AppraisalStandard) {
  standardForm.id = row?.id ?? "";
  standardForm.code = row?.code ?? "";
  standardForm.title = row?.title ?? "";
  standardForm.content = row?.content ?? "";
  standardForm.target_kfzt = row?.target_kfzt ?? "控制使用";
  standardForm.source = row?.source ?? "";
  standardKeywords.value = row?.keywords?.join(",") ?? "";
  showStandardEdit.value = true;
}

async function saveStandard() {
  if (!standardForm.code.trim() || !standardForm.title.trim() || !standardForm.content.trim()) {
    return message.warning("编码、名称、内容为必填");
  }
  const payload = {
    code: standardForm.code.trim(),
    title: standardForm.title.trim(),
    content: standardForm.content.trim(),
    target_kfzt: standardForm.target_kfzt,
    source: standardForm.source || undefined,
    keywords: standardKeywords.value
      ? standardKeywords.value.split(/[,，]/).map((s) => s.trim()).filter(Boolean)
      : undefined,
  };
  saving.value = true;
  try {
    const res = standardForm.id
      ? await AppraisalStandardAPI.update(standardForm.id, payload)
      : await AppraisalStandardAPI.create(payload);
    if (res.code === 0) {
      message.success("已保存");
      showStandardEdit.value = false;
      loadStandards();
    } else {
      message.error(res.message);
    }
  } finally {
    saving.value = false;
  }
}

async function toggleStandard(row: AppraisalStandard, enabled: boolean) {
  const res = await AppraisalStandardAPI.update(row.id, { is_enabled: enabled });
  if (res.code === 0) row.is_enabled = enabled;
  else message.error(res.message);
}

function removeStandard(row: AppraisalStandard) {
  dialog.warning({
    title: "删除条款",
    content: `确认删除条款 ${row.code}「${row.title}」？`,
    positiveText: "删除",
    negativeText: "取消",
    onPositiveClick: async () => {
      const res = await AppraisalStandardAPI.remove(row.id);
      if (res.code === 0) {
        message.success("已删除");
        loadStandards();
      } else {
        message.error(res.message);
      }
    },
  });
}

// ── 敏感词 ────────────────────────────────────────────────────────────────────
const words = ref<SensitiveWord[]>([]);
const wordsLoading = ref(false);
const wordKeyword = ref("");

async function loadWords() {
  wordsLoading.value = true;
  try {
    const res = await AppraisalStandardAPI.listWords({ keyword: wordKeyword.value || undefined, limit: 500 });
    words.value = res.data.items;
  } finally {
    wordsLoading.value = false;
  }
}

const wordColumns: DataTableColumns<SensitiveWord> = [
  { title: "敏感词", key: "word", width: 180 },
  { title: "类别", key: "category", width: 130, render: (r) => r.category ?? "—" },
  { title: "命中建议", key: "suggest_kfzt", width: 100, render: (r) => h(KfztTag, { value: r.suggest_kfzt }) },
  {
    title: "启用", key: "is_enabled", width: 70,
    render: (r) => h(NSwitch, {
      value: r.is_enabled,
      size: "small",
      onUpdateValue: (v: boolean) => toggleWord(r, v),
    }),
  },
  {
    title: "操作", key: "actions", width: 110,
    render: (r) => [
      h(NButton, { size: "tiny", tertiary: true, class: "mr-1", onClick: () => openWordEdit(r) }, { default: () => "编辑" }),
      h(NButton, { size: "tiny", tertiary: true, type: "error", onClick: () => removeWord(r) }, { default: () => "删除" }),
    ],
  },
];

const showWordEdit = ref(false);
const wordForm = reactive({
  id: "" as string,
  word: "",
  category: "",
  suggest_kfzt: "控制使用" as Kfzt,
});

function openWordEdit(row?: SensitiveWord) {
  wordForm.id = row?.id ?? "";
  wordForm.word = row?.word ?? "";
  wordForm.category = row?.category ?? "";
  wordForm.suggest_kfzt = row?.suggest_kfzt ?? "控制使用";
  showWordEdit.value = true;
}

async function saveWord() {
  if (!wordForm.word.trim()) return message.warning("敏感词不能为空");
  const payload = {
    word: wordForm.word.trim(),
    category: wordForm.category || undefined,
    suggest_kfzt: wordForm.suggest_kfzt,
  };
  saving.value = true;
  try {
    const res = wordForm.id
      ? await AppraisalStandardAPI.updateWord(wordForm.id, payload)
      : await AppraisalStandardAPI.createWord(payload);
    if (res.code === 0) {
      message.success("已保存");
      showWordEdit.value = false;
      loadWords();
    } else {
      message.error(res.message);
    }
  } finally {
    saving.value = false;
  }
}

async function toggleWord(row: SensitiveWord, enabled: boolean) {
  const res = await AppraisalStandardAPI.updateWord(row.id, { is_enabled: enabled });
  if (res.code === 0) row.is_enabled = enabled;
  else message.error(res.message);
}

function removeWord(row: SensitiveWord) {
  dialog.warning({
    title: "删除敏感词",
    content: `确认删除敏感词「${row.word}」？`,
    positiveText: "删除",
    negativeText: "取消",
    onPositiveClick: async () => {
      const res = await AppraisalStandardAPI.removeWord(row.id);
      if (res.code === 0) {
        message.success("已删除");
        loadWords();
      } else {
        message.error(res.message);
      }
    },
  });
}

onMounted(() => {
  loadStandards();
  loadWords();
});
</script>
