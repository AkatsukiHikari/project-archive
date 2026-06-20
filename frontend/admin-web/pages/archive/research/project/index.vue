<template>
  <div class="flex flex-col gap-4">
    <AdminPageHeader
      title="编研项目"
      description="编研项目立项、选材、成员分工与进度管理；从档案库挑选素材，产出编研成果"
      icon="heroicons:folder-open"
    />

    <!-- 工具栏 -->
    <div class="pro-card p-4 flex flex-wrap items-center gap-3">
      <NSelect
        v-model:value="filterStatus"
        :options="statusOptions"
        placeholder="全部状态"
        clearable
        style="width: 160px"
        @update:value="loadProjects"
      />
      <NButton tertiary @click="loadProjects">
        <template #icon><Icon name="heroicons:arrow-path" class="w-4 h-4" /></template>
        刷新
      </NButton>
      <div class="flex-1" />
      <NButton type="primary" @click="openCreate">
        <template #icon><Icon name="heroicons:plus" class="w-4 h-4" /></template>
        新建编研项目
      </NButton>
    </div>

    <!-- 项目列表 -->
    <div class="pro-card p-5">
      <ProTable :columns="columns" :data="projects" :loading="loading" :page-size="10" size="small" />
    </div>

    <!-- 新建 / 编辑项目 -->
    <NModal
      v-model:show="showForm"
      preset="card"
      :title="editingId ? '编辑编研项目' : '新建编研项目'"
      style="width: 720px; max-width: 95vw"
      :mask-closable="false"
    >
      <div class="grid grid-cols-2 gap-4">
        <div class="flex flex-col gap-1 col-span-2">
          <span class="text-sm font-medium">项目名称 <span class="text-red-500">*</span></span>
          <NInput v-model:value="form.title" placeholder="如：建市四十周年大事记编研" />
        </div>
        <div class="flex flex-col gap-1">
          <span class="text-sm font-medium">编研体裁 <span class="text-red-500">*</span></span>
          <NSelect v-model:value="form.project_type" :options="typeOptions" />
        </div>
        <div class="flex flex-col gap-1">
          <span class="text-sm font-medium">状态</span>
          <NSelect v-model:value="form.status" :options="statusOptions" />
        </div>
        <div class="flex flex-col gap-1">
          <span class="text-sm font-medium">主编</span>
          <NSelect v-model:value="form.editor_id" :options="userOptions" filterable clearable placeholder="负责编纂的人" />
        </div>
        <div class="flex flex-col gap-1">
          <span class="text-sm font-medium">审核员</span>
          <NSelect v-model:value="form.reviewer_id" :options="userOptions" filterable clearable placeholder="审核成果的人" />
        </div>
        <div class="flex flex-col gap-1">
          <span class="text-sm font-medium">起始日期</span>
          <NDatePicker v-model:formatted-value="form.start_date" value-format="yyyy-MM-dd" type="date" clearable />
        </div>
        <div class="flex flex-col gap-1">
          <span class="text-sm font-medium">结束日期</span>
          <NDatePicker v-model:formatted-value="form.end_date" value-format="yyyy-MM-dd" type="date" clearable />
        </div>
        <div class="flex flex-col gap-1 col-span-2">
          <span class="text-sm font-medium">编研成员</span>
          <NDynamicTags v-model:value="form.members" />
        </div>
        <div class="flex flex-col gap-1 col-span-2">
          <span class="text-sm font-medium">编研目的</span>
          <NInput v-model:value="form.purpose" type="textarea" :rows="2" placeholder="可选" />
        </div>
      </div>
      <template #footer>
        <div class="flex justify-end gap-3">
          <NButton @click="showForm = false">取消</NButton>
          <NButton type="primary" :loading="saving" @click="submitForm">保存</NButton>
        </div>
      </template>
    </NModal>

    <!-- 项目详情 + 选材 -->
    <NDrawer v-model:show="showDetail" :width="760" placement="right">
      <NDrawerContent v-if="detail" :title="detail.title" closable>
        <div class="flex flex-col gap-5">
          <!-- 概览 -->
          <div class="flex flex-wrap items-center gap-3 text-sm text-gray-500">
            <ResearchTypeTag :type="detail.project_type" />
            <NTag :type="detail.status === 'completed' ? 'success' : 'info'" size="small" round>
              {{ detail.status === "completed" ? "已完成" : "进行中" }}
            </NTag>
            <span v-if="detail.editor_name">主编 {{ detail.editor_name }}</span>
            <span v-if="detail.reviewer_name">· 审核 {{ detail.reviewer_name }}</span>
            <span v-if="detail.start_date">· {{ detail.start_date }} ~ {{ detail.end_date || "今" }}</span>
          </div>
          <p v-if="detail.purpose" class="text-sm text-gray-600 bg-gray-50 rounded-lg p-3">{{ detail.purpose }}</p>

          <!-- 选材 -->
          <div class="flex items-center justify-between">
            <p class="text-sm font-medium">
              已选素材
              <span class="text-gray-400 font-normal ml-1">{{ materials.length }} 件</span>
            </p>
            <NButton size="small" type="primary" tertiary @click="openPicker">
              <template #icon><Icon name="heroicons:plus" class="w-4 h-4" /></template>
              从档案库选材
            </NButton>
          </div>
          <ProTable :columns="materialColumns" :data="materials" :loading="materialLoading" :page-size="0" size="small" max-height="280" />

          <!-- 关联成果 -->
          <div class="flex items-center justify-between">
            <p class="text-sm font-medium">
              编研成果
              <span class="text-gray-400 font-normal ml-1">{{ detail.result_count }} 项</span>
            </p>
            <NButton size="small" tertiary @click="goCompilation(detail.id)">
              <template #icon><Icon name="heroicons:arrow-top-right-on-square" class="w-4 h-4" /></template>
              前往成果库编纂
            </NButton>
          </div>
        </div>
      </NDrawerContent>
    </NDrawer>

    <!-- 选材弹窗（与成果档案库共用同一选档器：分页 + 查看原文） -->
    <ArchivePickerModal
      ref="pickerRef"
      v-model:show="showPicker"
      title="从馆藏选材加入项目"
      :exclude-ids="materialArchiveIds"
      @confirm="confirmAdd"
      @view="openViewer"
    />

    <!-- 原文查看器 -->
    <NDrawer v-model:show="viewerShow" :width="viewerWidth" placement="right">
      <NDrawerContent :body-content-style="{ padding: 0, height: '100%' }" closable>
        <template #header>档案原文</template>
        <ArchiveSourceViewer :archive-id="viewerArchiveId" :title="viewerTitle" :dh="viewerDh" />
      </NDrawerContent>
    </NDrawer>
  </div>
</template>

<script setup lang="tsx">
import { computed, h, nextTick, onMounted, reactive, ref } from "vue";
import {
  NButton, NDatePicker, NDrawer, NDrawerContent, NDynamicTags,
  NInput, NModal, NPopconfirm, NSelect, NTag, useMessage,
} from "naive-ui";
import type { DataTableColumns } from "naive-ui";
import { AdminPageHeader } from "@/components/admin";
import { ProTable } from "@/components/ui";
import { ArchivePickerModal, ArchiveSourceViewer, ResearchTypeTag } from "@/components/archive";
import {
  RESULT_TYPES, ResearchProjectAPI,
  type ProjectPayload, type ProjectStatus, type ResearchMaterial, type ResearchProject, type ResultType,
} from "@/api/research";
import { UserAPI, type User } from "@/api/iam";

definePageMeta({ layout: "archive", middleware: "auth" });

const message = useMessage();
const router = useRouter();

const statusOptions = [
  { label: "进行中", value: "in_progress" },
  { label: "已完成", value: "completed" },
];
const typeOptions = RESULT_TYPES.map((t) => ({ label: t, value: t }));

// ── 列表 ──────────────────────────────────────────────────────────────────────
const loading = ref(false);
const projects = ref<ResearchProject[]>([]);
const filterStatus = ref<ProjectStatus | null>(null);

async function loadProjects() {
  loading.value = true;
  try {
    const res = await ResearchProjectAPI.list({ status: filterStatus.value ?? undefined });
    projects.value = res.data;
  } finally {
    loading.value = false;
  }
}

const columns: DataTableColumns<ResearchProject> = [
  { title: "项目名称", key: "title", ellipsis: { tooltip: true } },
  { title: "体裁", key: "project_type", width: 110, render: (r) => h(ResearchTypeTag, { type: r.project_type }) },
  { title: "主编", key: "editor_name", width: 100, render: (r) => r.editor_name || "—" },
  { title: "审核员", key: "reviewer_name", width: 100, render: (r) => r.reviewer_name || "—" },
  { title: "素材", key: "material_count", width: 70, render: (r) => `${r.material_count} 件` },
  { title: "成果", key: "result_count", width: 70, render: (r) => `${r.result_count} 项` },
  {
    title: "状态", key: "status", width: 90,
    render: (r) => h(NTag, { type: r.status === "completed" ? "success" : "info", size: "small", round: true },
      { default: () => (r.status === "completed" ? "已完成" : "进行中") }),
  },
  { title: "创建时间", key: "create_time", width: 110, render: (r) => r.create_time?.slice(0, 10) },
  {
    title: "操作", key: "actions", width: 180,
    render: (r) => h("div", { class: "flex gap-1" }, [
      h(NButton, { size: "small", tertiary: true, onClick: () => openDetail(r.id) }, { default: () => "详情" }),
      h(NButton, { size: "small", tertiary: true, onClick: () => openEdit(r) }, { default: () => "编辑" }),
      h(NPopconfirm, { onPositiveClick: () => removeProject(r.id) }, {
        trigger: () => h(NButton, { size: "small", tertiary: true, type: "error" }, { default: () => "删除" }),
        default: () => "确认删除该项目？素材将一并移除。",
      }),
    ]),
  },
];

// ── 新建 / 编辑 ────────────────────────────────────────────────────────────────
const showForm = ref(false);
const saving = ref(false);
const editingId = ref<string | null>(null);
const form = reactive<ProjectPayload & { members: string[] }>({
  title: "", project_type: "专题汇编" as ResultType, status: "in_progress",
  editor_id: null, reviewer_id: null, members: [], start_date: null, end_date: null, purpose: null,
});

function resetForm() {
  form.title = "";
  form.project_type = "专题汇编";
  form.status = "in_progress";
  form.editor_id = null;
  form.reviewer_id = null;
  form.members = [];
  form.start_date = null;
  form.end_date = null;
  form.purpose = null;
}

function openCreate() {
  editingId.value = null;
  resetForm();
  showForm.value = true;
}

function openEdit(p: ResearchProject) {
  editingId.value = p.id;
  form.title = p.title;
  form.project_type = p.project_type;
  form.status = p.status;
  form.editor_id = p.editor_id ?? null;
  form.reviewer_id = p.reviewer_id ?? null;
  form.members = [...(p.members ?? [])];
  form.start_date = p.start_date ?? null;
  form.end_date = p.end_date ?? null;
  form.purpose = p.purpose ?? null;
  showForm.value = true;
}

async function submitForm() {
  if (!form.title.trim()) return message.warning("请填写项目名称");
  saving.value = true;
  try {
    const payload: ProjectPayload = {
      title: form.title.trim(),
      project_type: form.project_type,
      status: form.status,
      editor_id: form.editor_id || null,
      reviewer_id: form.reviewer_id || null,
      members: form.members,
      start_date: form.start_date || null,
      end_date: form.end_date || null,
      purpose: form.purpose || null,
    };
    const res = editingId.value
      ? await ResearchProjectAPI.update(editingId.value, payload)
      : await ResearchProjectAPI.create(payload);
    if (res.code === 0) {
      message.success("保存成功");
      showForm.value = false;
      loadProjects();
    } else {
      message.error(res.message);
    }
  } finally {
    saving.value = false;
  }
}

async function removeProject(id: string) {
  const res = await ResearchProjectAPI.remove(id);
  if (res.code === 0) {
    message.success("已删除");
    loadProjects();
  } else {
    message.error(res.message);
  }
}

// ── 详情 + 选材 ────────────────────────────────────────────────────────────────
const showDetail = ref(false);
const detail = ref<ResearchProject | null>(null);
const materials = ref<ResearchMaterial[]>([]);
const materialLoading = ref(false);

async function openDetail(id: string) {
  const res = await ResearchProjectAPI.get(id);
  detail.value = res.data;
  showDetail.value = true;
  loadMaterials(id);
}

async function loadMaterials(id: string) {
  materialLoading.value = true;
  try {
    const res = await ResearchProjectAPI.listMaterials(id);
    materials.value = res.data;
  } finally {
    materialLoading.value = false;
  }
}

const materialColumns: DataTableColumns<ResearchMaterial> = [
  { title: "档号", key: "DH", width: 150, render: (r) => r.DH || "—" },
  { title: "题名", key: "TM", ellipsis: { tooltip: true } },
  { title: "责任者", key: "RZZ", width: 120, render: (r) => r.RZZ || "—" },
  { title: "文件日期", key: "WJRQ", width: 110, render: (r) => r.WJRQ || (r.ND ? `${r.ND}` : "—") },
  {
    title: "操作", key: "actions", width: 150,
    render: (r) => h("div", { class: "flex gap-1" }, [
      h(NButton, { size: "small", tertiary: true, onClick: () => openViewer({ archive_id: r.archive_id, TM: r.TM, DH: r.DH || "" }) },
        { default: () => "查看原文" }),
      h(NPopconfirm, { onPositiveClick: () => removeMaterial(r.id) }, {
        trigger: () => h(NButton, { size: "small", tertiary: true, type: "error" }, { default: () => "移除" }),
        default: () => "从素材中移除该档案？",
      }),
    ]),
  },
];

async function removeMaterial(materialId: string) {
  const res = await ResearchProjectAPI.removeMaterial(materialId);
  if (res.code === 0 && detail.value) {
    message.success("已移除");
    loadMaterials(detail.value.id);
    detail.value = { ...detail.value, material_count: Math.max(0, detail.value.material_count - 1) };
  }
}

function goCompilation(projectId: string) {
  router.push({ path: "/archive/research/compilation", query: { project_id: projectId } });
}

// ── 选材弹窗（共用 ArchivePickerModal）─────────────────────────────────────────
const showPicker = ref(false);
const pickerRef = ref<{ reset: () => void } | null>(null);
const materialArchiveIds = computed(() => materials.value.map((m) => m.archive_id));

function openPicker() {
  showPicker.value = true;
  nextTick(() => pickerRef.value?.reset());
}

async function confirmAdd(ids: string[]) {
  if (!detail.value) return;
  try {
    const res = await ResearchProjectAPI.addMaterials(detail.value.id, ids);
    if (res.code === 0) {
      showPicker.value = false;
      message.success(`已加入 ${res.data.added} 件素材`);
      loadMaterials(detail.value.id);
      detail.value = { ...detail.value, material_count: detail.value.material_count + res.data.added };
    } else {
      message.error(res.message);
    }
  } catch {
    message.error("加入失败，请重试");
  }
}

// ── 原文查看器 ────────────────────────────────────────────────────────────────
const viewerShow = ref(false);
const viewerArchiveId = ref<string | null>(null);
const viewerTitle = ref("");
const viewerDh = ref("");
const viewerWidth = computed(() => Math.round((typeof window !== "undefined" ? window.innerWidth : 1280) * 0.66));

function openViewer(a: { archive_id: string; TM: string; DH: string }) {
  viewerArchiveId.value = a.archive_id;
  viewerTitle.value = a.TM;
  viewerDh.value = a.DH;
  viewerShow.value = true;
}

// ── 用户下拉 ──────────────────────────────────────────────────────────────────
const userOptions = ref<{ label: string; value: string }[]>([]);
async function loadUsers() {
  const res = await UserAPI.list();
  userOptions.value = (res.data ?? []).map((u: User) => ({
    label: u.full_name ? `${u.full_name}（${u.username}）` : u.username,
    value: u.id,
  }));
}

onMounted(() => {
  loadProjects();
  loadUsers();
});
</script>
