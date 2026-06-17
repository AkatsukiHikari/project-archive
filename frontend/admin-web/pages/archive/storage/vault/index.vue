<template>
  <div class="flex flex-col gap-4">
    <AdminPageHeader
      title="库房管理"
      description="档案库房架体布局、容量与温湿度管理，支持三维架位可视化"
      icon="heroicons:home-modern"
    />

    <!-- KPI -->
    <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
      <KpiCard label="库房数量" :value="String(vaults.length)" sub="间" icon="heroicons:building-office-2" icon-bg="rgba(59,130,246,0.1)" icon-color="#3b82f6" />
      <KpiCard label="设计总容量" :value="totalCapacity.toLocaleString()" sub="卷/件" icon="heroicons:cube" icon-bg="rgba(16,185,129,0.1)" icon-color="#10b981" />
      <KpiCard label="已用容量" :value="totalUsed.toLocaleString()" sub="卷/件" icon="heroicons:archive-box" icon-bg="rgba(245,158,11,0.1)" icon-color="#f59e0b" />
      <KpiCard label="整体填充率" :value="`${overallFill}%`" sub="平均占用" icon="heroicons:chart-pie" icon-bg="rgba(139,92,246,0.1)" icon-color="#8b5cf6" />
    </div>

    <div class="flex items-center">
      <div class="flex-1" />
      <NButton type="primary" @click="openEdit(null)">
        <template #icon><Icon name="heroicons:plus" class="w-4 h-4" /></template>
        新建库房
      </NButton>
    </div>

    <!-- 库房卡片 -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      <div
        v-for="v in vaults"
        :key="v.id"
        class="pro-card p-5 cursor-pointer transition-all hover:shadow-lg"
        @click="openDetail(v)"
      >
        <div class="flex items-start justify-between">
          <div>
            <p class="text-[15px] font-semibold m-0" style="color:var(--semi-color-text-0)">{{ v.name }}</p>
            <p class="text-[12px] m-0 mt-0.5" style="color:var(--semi-color-text-3)">{{ v.code }} · {{ v.location || "—" }}</p>
          </div>
          <NTag size="small" :type="statusType(v.status)" round>{{ statusLabel(v.status) }}</NTag>
        </div>

        <!-- 填充率环 -->
        <div class="flex items-center gap-4 mt-4">
          <NProgress
            type="circle"
            :percentage="v.fill_rate"
            :stroke-width="9"
            :color="fillColor(v.fill_rate)"
            :style="{ width: '72px' }"
          >
            <span class="text-[14px] font-bold">{{ v.fill_rate }}%</span>
          </NProgress>
          <div class="flex-1 flex flex-col gap-1.5 text-[12px]">
            <div class="flex justify-between">
              <span style="color:var(--semi-color-text-3)">容量</span>
              <span style="color:var(--semi-color-text-1)">{{ v.used.toLocaleString() }} / {{ v.capacity.toLocaleString() }}</span>
            </div>
            <div class="flex justify-between">
              <span style="color:var(--semi-color-text-3)">温度</span>
              <span :style="tempStyle(v.temperature)">{{ v.temperature ?? "—" }} ℃</span>
            </div>
            <div class="flex justify-between">
              <span style="color:var(--semi-color-text-3)">湿度</span>
              <span :style="humidityStyle(v.humidity)">{{ v.humidity ?? "—" }} %RH</span>
            </div>
            <div class="flex justify-between">
              <span style="color:var(--semi-color-text-3)">架体</span>
              <span style="color:var(--semi-color-text-1)">{{ v.rows }}×{{ v.columns }}×{{ v.layers }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 库房详情（三维架位） -->
    <NModal
      v-model:show="showDetail"
      preset="card"
      :title="`${detail?.name ?? ''} · 架位布局`"
      style="width: 1000px; max-width: 96vw"
    >
      <div v-if="detail" class="flex flex-col gap-4">
        <div class="flex items-center gap-4 text-[13px]" style="color:var(--semi-color-text-2)">
          <span>{{ detail.code }}</span>
          <span>{{ detail.location }}</span>
          <span>面积 {{ detail.area_sqm ?? "—" }} ㎡</span>
          <span>填充率 <b :style="`color:${fillColor(detail.fill_rate)}`">{{ detail.fill_rate }}%</b></span>
          <div class="flex-1" />
          <NButton size="small" tertiary @click="openEdit(detail)">编辑</NButton>
          <NButton size="small" tertiary type="error" @click="confirmDelete(detail)">删除</NButton>
        </div>

        <ClientOnly>
          <VaultShelf3D
            v-if="detail.shelves"
            :shelves="detail.shelves"
            :rows="detail.rows"
            :columns="detail.columns"
            :layers="detail.layers"
            @pick="onShelfPick"
          />
          <template #fallback>
            <div class="rounded-xl flex items-center justify-center" style="height:460px;background:#1c2742;color:#8fa0c4">
              三维库房加载中…
            </div>
          </template>
        </ClientOnly>
        <p class="text-center text-[12px] m-0" style="color:var(--semi-color-text-3)">
          点击架位可管理其档案（上架 / 下架 / 改容量）
        </p>
      </div>
    </NModal>

    <!-- 架位管理抽屉 -->
    <ShelfManageDrawer
      v-model:show="shelfDrawer"
      :shelf-id="activeShelfId"
      @changed="reloadDetail"
    />

    <!-- 新建 / 编辑库房 -->
    <NModal
      v-model:show="showEdit"
      preset="card"
      :title="form.id ? '编辑库房' : '新建库房'"
      style="width: 560px; max-width: 95vw"
    >
      <div class="grid grid-cols-2 gap-4">
        <Field label="库房编号" required><NInput v-model:value="form.code" :disabled="!!form.id" placeholder="如 KF-E" /></Field>
        <Field label="库房名称" required><NInput v-model:value="form.name" placeholder="如 五号档案库" /></Field>
        <Field label="位置"><NInput v-model:value="form.location" placeholder="楼层 / 区域" /></Field>
        <Field label="面积（㎡）"><NInputNumber v-model:value="form.area_sqm" :show-button="false" class="w-full" /></Field>
        <Field label="排数"><NInputNumber v-model:value="form.rows" :min="1" :max="20" class="w-full" /></Field>
        <Field label="每排列数"><NInputNumber v-model:value="form.columns" :min="1" :max="30" class="w-full" /></Field>
        <Field label="每列层数"><NInputNumber v-model:value="form.layers" :min="1" :max="12" class="w-full" /></Field>
        <Field label="设计容量（卷/件）"><NInputNumber v-model:value="form.capacity" :min="0" class="w-full" /></Field>
        <Field label="温度（℃）"><NInputNumber v-model:value="form.temperature" :show-button="false" class="w-full" /></Field>
        <Field label="湿度（%RH）"><NInputNumber v-model:value="form.humidity" :show-button="false" class="w-full" /></Field>
        <Field label="状态">
          <NSelect v-model:value="form.status" :options="statusOptions" />
        </Field>
      </div>
      <template #footer>
        <div class="flex justify-end gap-3">
          <NButton @click="showEdit = false">取消</NButton>
          <NButton type="primary" :loading="saving" @click="submit">保存</NButton>
        </div>
      </template>
    </NModal>
  </div>
</template>

<script setup lang="tsx">
import { computed, h, onMounted, reactive, ref } from "vue";
import { NButton, NInput, NInputNumber, NModal, NProgress, NSelect, NTag, useDialog, useMessage } from "naive-ui";
import { AdminPageHeader, KpiCard } from "@/components/admin";
import { ShelfManageDrawer, VaultShelf3D } from "@/components/archive";
import { StorageAPI } from "@/api/storage";
import type { Shelf, Vault, VaultStatus } from "@/api/storage";

definePageMeta({ layout: "archive", middleware: "auth" });

const message = useMessage();
const dialog = useDialog();

type SlotsCtx = { slots: { default?: () => unknown } };
const Field = (props: { label: string; required?: boolean }, { slots }: SlotsCtx) =>
  h("div", { class: "flex flex-col gap-1" }, [
    h("span", { class: "text-[12px]", style: "color:var(--semi-color-text-3)" }, [
      props.label,
      props.required ? h("span", { class: "text-red-500 ml-0.5" }, "*") : null,
    ]),
    slots.default?.(),
  ]);

const statusOptions = [
  { label: "在用", value: "active" },
  { label: "维护", value: "maintenance" },
  { label: "停用", value: "disabled" },
];

const vaults = ref<Vault[]>([]);
const totalCapacity = computed(() => vaults.value.reduce((s, v) => s + v.capacity, 0));
const totalUsed = computed(() => vaults.value.reduce((s, v) => s + v.used, 0));
const overallFill = computed(() => (totalCapacity.value ? Math.round((totalUsed.value / totalCapacity.value) * 100) : 0));

function statusLabel(s: VaultStatus): string {
  return { active: "在用", maintenance: "维护中", disabled: "停用" }[s] ?? s;
}
function statusType(s: VaultStatus): "success" | "warning" | "default" {
  return { active: "success", maintenance: "warning", disabled: "default" }[s] as never;
}
function fillColor(p: number): string {
  if (p >= 90) return "#ef4444";
  if (p >= 70) return "#f59e0b";
  return "#10b981";
}
function tempStyle(t?: number | null): string {
  if (t == null) return "color:var(--semi-color-text-1)";
  return t < 14 || t > 24 ? "color:#ef4444;font-weight:600" : "color:var(--semi-color-text-1)";
}
function humidityStyle(hm?: number | null): string {
  if (hm == null) return "color:var(--semi-color-text-1)";
  return hm < 45 || hm > 60 ? "color:#ef4444;font-weight:600" : "color:var(--semi-color-text-1)";
}

async function load() {
  const res = await StorageAPI.listVaults();
  if (res.code === 0) vaults.value = res.data;
}

// ── 详情 ──
const showDetail = ref(false);
const detail = ref<Vault | null>(null);

async function openDetail(v: Vault) {
  const res = await StorageAPI.getVault(v.id);
  if (res.code === 0) {
    detail.value = res.data;
    showDetail.value = true;
  }
}

async function reloadDetail() {
  if (detail.value) {
    const res = await StorageAPI.getVault(detail.value.id);
    if (res.code === 0) detail.value = res.data;
  }
  load();  // 同步刷新库房卡片占用率
}

// ── 架位管理抽屉 ──
const shelfDrawer = ref(false);
const activeShelfId = ref<string | null>(null);

function onShelfPick(s: Shelf) {
  activeShelfId.value = s.id;
  shelfDrawer.value = true;
}

// ── 新建 / 编辑 ──
const showEdit = ref(false);
const saving = ref(false);
const form = reactive({
  id: "" as string,
  code: "", name: "", location: "",
  area_sqm: null as number | null,
  rows: 4, columns: 6, layers: 5, capacity: 5000,
  temperature: 20 as number | null,
  humidity: 50 as number | null,
  status: "active" as VaultStatus,
});

function openEdit(v: Vault | null) {
  if (v) {
    Object.assign(form, {
      id: v.id, code: v.code, name: v.name, location: v.location ?? "",
      area_sqm: v.area_sqm ?? null, rows: v.rows, columns: v.columns, layers: v.layers,
      capacity: v.capacity, temperature: v.temperature ?? null, humidity: v.humidity ?? null,
      status: v.status,
    });
  } else {
    Object.assign(form, {
      id: "", code: "", name: "", location: "", area_sqm: null,
      rows: 4, columns: 6, layers: 5, capacity: 5000, temperature: 20, humidity: 50, status: "active",
    });
  }
  showEdit.value = true;
}

async function submit() {
  if (!form.code.trim() || !form.name.trim()) return message.warning("库房编号和名称必填");
  const payload = {
    code: form.code.trim(), name: form.name.trim(), location: form.location || undefined,
    area_sqm: form.area_sqm ?? undefined, rows: form.rows, columns: form.columns, layers: form.layers,
    capacity: form.capacity, temperature: form.temperature ?? undefined,
    humidity: form.humidity ?? undefined, status: form.status,
  };
  saving.value = true;
  try {
    const res = form.id
      ? await StorageAPI.updateVault(form.id, payload)
      : await StorageAPI.createVault(payload);
    if (res.code === 0) {
      message.success("已保存");
      showEdit.value = false;
      showDetail.value = false;
      await load();
    } else {
      message.error(res.message);
    }
  } finally {
    saving.value = false;
  }
}

function confirmDelete(v: Vault) {
  dialog.warning({
    title: "删除库房",
    content: `确认删除库房「${v.name}」及其架位？`,
    positiveText: "删除",
    negativeText: "取消",
    onPositiveClick: async () => {
      const res = await StorageAPI.deleteVault(v.id);
      if (res.code === 0) {
        message.success("已删除");
        showDetail.value = false;
        await load();
      } else {
        message.error(res.message);
      }
    },
  });
}

onMounted(load);
</script>
