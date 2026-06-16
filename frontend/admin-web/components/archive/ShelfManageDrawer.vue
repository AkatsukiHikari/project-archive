<template>
  <NDrawer :show="show" :width="520" placement="right" @update:show="(v: boolean) => emit('update:show', v)">
    <NDrawerContent v-if="detail" :title="`架位 ${detail.code}`" closable>
      <div class="flex flex-col gap-4">
        <!-- 容量 / 占用 -->
        <div class="pro-card p-4 flex items-center gap-4">
          <NProgress
            type="circle"
            :percentage="fillRate"
            :stroke-width="9"
            :color="fillColor"
            :style="{ width: '64px' }"
          >
            <span class="text-[13px] font-bold">{{ fillRate }}%</span>
          </NProgress>
          <div class="flex-1 flex flex-col gap-1.5 text-[13px]">
            <div class="flex items-center gap-2">
              <span style="color:var(--semi-color-text-3)">容量</span>
              <NInputNumber v-model:value="editCapacity" size="small" :min="0" :show-button="false" style="width: 100px" />
              <span style="color:var(--semi-color-text-3)">已用 {{ detail.used }}</span>
              <NButton size="tiny" tertiary :loading="savingCap" @click="saveCapacity">保存容量</NButton>
            </div>
            <div class="flex items-center gap-2">
              <span style="color:var(--semi-color-text-3)">标注</span>
              <NInput v-model:value="editLabel" size="small" placeholder="存放范围标注" style="width: 220px" @blur="saveLabel" />
            </div>
          </div>
        </div>

        <!-- 架位上的档案 -->
        <div class="flex items-center justify-between">
          <span class="text-[13px] font-medium" style="color:var(--semi-color-text-0)">
            架位档案（{{ detail.archives.length }}）
          </span>
          <NButton size="small" type="primary" @click="openPicker">
            <template #icon><Icon name="heroicons:plus" class="w-4 h-4" /></template>
            上架档案
          </NButton>
        </div>

        <div
          v-if="!detail.archives.length"
          class="py-6 text-center rounded-lg text-[12px]"
          style="background:var(--semi-color-fill-0);color:var(--semi-color-text-3)"
        >
          该架位暂无档案，点击"上架档案"放入
        </div>
        <div
          v-for="a in detail.archives"
          :key="a.id"
          class="flex items-center gap-2 px-3 py-2 rounded-lg"
          style="background:var(--semi-color-fill-0)"
        >
          <div class="flex-1 min-w-0">
            <p class="text-[12.5px] truncate m-0" style="color:var(--semi-color-text-0)">{{ a.TM }}</p>
            <p class="text-[11px] m-0 mt-0.5 font-mono" style="color:var(--semi-color-text-3)">{{ a.DH || "—" }} · {{ a.ND || "—" }}</p>
          </div>
          <NButton size="tiny" quaternary type="error" @click="unshelve(a)">下架</NButton>
        </div>
      </div>
    </NDrawerContent>
  </NDrawer>

  <!-- 上架挑选 -->
  <NModal v-model:show="showPicker" preset="card" title="上架档案" style="width: 640px; max-width: 95vw">
    <div class="flex flex-col gap-3">
      <div class="flex items-center gap-2">
        <NInput v-model:value="pickerKeyword" placeholder="题名 / 档号" clearable style="width: 260px" @keydown.enter="loadUnshelved" />
        <NButton tertiary @click="loadUnshelved">查询</NButton>
        <span class="text-[12px]" style="color:var(--semi-color-text-3)">从正式库未上架档案中选择</span>
      </div>
      <div class="max-h-[360px] overflow-auto flex flex-col gap-1">
        <label
          v-for="a in candidates"
          :key="a.id"
          class="flex items-center gap-2 px-3 py-2 rounded-lg cursor-pointer"
          style="background:var(--semi-color-fill-0)"
        >
          <NCheckbox :checked="picked.has(a.id)" @update:checked="(v: boolean) => togglePick(a.id, v)" />
          <div class="flex-1 min-w-0">
            <p class="text-[12.5px] truncate m-0">{{ a.TM }}</p>
            <p class="text-[11px] m-0 font-mono" style="color:var(--semi-color-text-3)">{{ a.DH || "—" }} · {{ a.ND || "—" }}</p>
          </div>
        </label>
        <div v-if="!candidates.length" class="py-6 text-center text-[12px]" style="color:var(--semi-color-text-3)">
          没有待上架的档案
        </div>
      </div>
    </div>
    <template #footer>
      <div class="flex justify-end gap-3">
        <NButton @click="showPicker = false">取消</NButton>
        <NButton type="primary" :disabled="!picked.size" :loading="assigning" @click="doAssign">
          上架（{{ picked.size }}）
        </NButton>
      </div>
    </template>
  </NModal>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { NButton, NCheckbox, NDrawer, NDrawerContent, NInput, NInputNumber, NModal, NProgress, useMessage } from "naive-ui";
import { StorageAPI } from "@/api/storage";
import type { ShelfArchive, ShelfDetail } from "@/api/storage";

const props = defineProps<{ show: boolean; shelfId: string | null }>();
const emit = defineEmits<{ "update:show": [boolean]; changed: [] }>();

const message = useMessage();
const detail = ref<ShelfDetail | null>(null);
const editCapacity = ref<number | null>(null);
const editLabel = ref("");
const savingCap = ref(false);

const fillRate = computed(() => {
  const d = detail.value;
  return d && d.capacity ? Math.round((d.used / d.capacity) * 100) : 0;
});
const fillColor = computed(() => {
  const p = fillRate.value;
  return p >= 90 ? "#ef4444" : p >= 70 ? "#f59e0b" : "#10b981";
});

async function loadDetail() {
  if (!props.shelfId) return;
  const res = await StorageAPI.getShelf(props.shelfId);
  if (res.code === 0) {
    detail.value = res.data;
    editCapacity.value = res.data.capacity;
    editLabel.value = res.data.label ?? "";
  }
}

watch(() => [props.show, props.shelfId], () => {
  if (props.show && props.shelfId) loadDetail();
});

async function saveCapacity() {
  if (!props.shelfId || editCapacity.value == null) return;
  savingCap.value = true;
  try {
    const res = await StorageAPI.updateShelf(props.shelfId, { capacity: editCapacity.value });
    if (res.code === 0) { message.success("容量已更新"); await loadDetail(); emit("changed"); }
    else message.error(res.message);
  } finally {
    savingCap.value = false;
  }
}

async function saveLabel() {
  if (!props.shelfId) return;
  if ((detail.value?.label ?? "") === editLabel.value) return;
  await StorageAPI.updateShelf(props.shelfId, { label: editLabel.value });
}

async function unshelve(a: ShelfArchive) {
  const res = await StorageAPI.unassignFromShelf([a.id]);
  if (res.code === 0) { message.success(`已下架《${a.TM}》`); await loadDetail(); emit("changed"); }
  else message.error(res.message);
}

// ── 上架挑选 ──
const showPicker = ref(false);
const pickerKeyword = ref("");
const candidates = ref<ShelfArchive[]>([]);
const picked = ref<Set<string>>(new Set());
const assigning = ref(false);

async function openPicker() {
  pickerKeyword.value = "";
  picked.value = new Set();
  showPicker.value = true;
  await loadUnshelved();
}
async function loadUnshelved() {
  const res = await StorageAPI.unshelved(pickerKeyword.value || undefined);
  if (res.code === 0) candidates.value = res.data;
}
function togglePick(id: string, v: boolean) {
  const s = new Set(picked.value);
  if (v) s.add(id); else s.delete(id);
  picked.value = s;
}
async function doAssign() {
  if (!props.shelfId || !picked.value.size) return;
  assigning.value = true;
  try {
    const res = await StorageAPI.assignToShelf(props.shelfId, [...picked.value]);
    if (res.code === 0) {
      message.success(`已上架 ${res.data.assigned} 件`);
      showPicker.value = false;
      await loadDetail();
      emit("changed");
    } else {
      message.error(res.message);
    }
  } finally {
    assigning.value = false;
  }
}
</script>
