<template>
  <div class="flex flex-col gap-4">
    <NSpin v-if="loading" size="small" />
    <template v-else-if="detail">
      <!-- 利用人信息 -->
      <div class="flex items-start gap-3">
        <PersonAvatar :name="detail.applicant_name" :size="48" />
        <div class="flex-1 min-w-0">
          <div class="flex items-center gap-2">
            <span class="text-[15px] font-semibold" style="color:var(--semi-color-text-0)">{{ detail.applicant_name }}</span>
            <NTag :type="statusTone" size="small" round>{{ statusLabel }}</NTag>
          </div>
          <div class="text-[12px] mt-0.5" style="color:var(--semi-color-text-3)">登记号 {{ detail.reg_no }}</div>
        </div>
      </div>

      <table class="w-full text-[13px] border-collapse">
        <tbody>
          <tr v-for="f in infoFields" :key="f.label" class="border-b" style="border-color:var(--semi-color-border)">
            <th class="text-left align-top py-1.5 pr-3 font-medium whitespace-nowrap" style="width:84px;color:var(--semi-color-text-3)">{{ f.label }}</th>
            <td class="py-1.5 break-words" style="color:var(--semi-color-text-0)">{{ f.value || "—" }}</td>
          </tr>
        </tbody>
      </table>

      <!-- 调阅篮 -->
      <div class="flex flex-col gap-2">
        <div class="flex items-center gap-2">
          <Icon name="heroicons:shopping-bag" class="w-4 h-4" style="color:oklch(var(--p))" />
          <span class="text-[13px] font-semibold" style="color:var(--semi-color-text-0)">调阅篮</span>
          <span class="text-[12px]" style="color:var(--semi-color-text-3)">{{ detail.items.length }} 件</span>
        </div>
        <div v-if="detail.items.length === 0" class="text-[12px] py-4 text-center" style="color:var(--semi-color-text-3)">
          暂无调阅档案
        </div>
        <div v-else class="flex flex-col gap-1.5">
          <div
            v-for="(it, i) in detail.items"
            :key="it.id"
            class="flex items-center gap-2 rounded-lg border px-3 py-2"
            style="border-color:var(--semi-color-border)"
          >
            <span class="text-[12px] tabular-nums" style="color:var(--semi-color-text-3)">{{ i + 1 }}</span>
            <div class="flex-1 min-w-0">
              <div class="text-[12.5px] truncate" style="color:var(--semi-color-text-0)">{{ it.TM }}</div>
              <div class="text-[11px]" style="color:var(--semi-color-text-3)">
                <span class="font-mono">{{ it.DH || "—" }}</span> · {{ it.ND || "—" }} 年
              </div>
            </div>
            <NButton size="tiny" tertiary @click="openReader(it.archive_id)">原文</NButton>
            <NButton
              v-if="detail.status === 'processing'"
              size="tiny"
              tertiary
              type="error"
              @click="removeItem(it.id)"
            >
              <Icon name="heroicons:x-mark" class="w-3.5 h-3.5" />
            </NButton>
          </div>
        </div>
      </div>

      <!-- 操作 -->
      <div v-if="showActions && detail.status === 'processing'" class="flex gap-2 pt-2 border-t" style="border-color:var(--semi-color-border)">
        <NButton type="primary" @click="goProcess">
          <template #icon><Icon name="heroicons:magnifying-glass" class="w-4 h-4" /></template>
          去办理（查档）
        </NButton>
        <NButton type="success" :loading="completing" @click="complete">
          <template #icon><Icon name="heroicons:check-circle" class="w-4 h-4" /></template>
          办理完成
        </NButton>
      </div>
    </template>
    <div v-else class="text-[12px] py-6 text-center" style="color:var(--semi-color-text-3)">未找到登记信息</div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from "vue";
import { useRouter } from "vue-router";
import { NSpin, NTag, NButton, useMessage } from "naive-ui";
import { PersonAvatar } from "@/components/archive";
import { UtilizationAPI } from "@/api/utilization";
import type { UtilApplicationDetail } from "@/api/utilization";

const props = withDefaults(defineProps<{ appId?: string | null; showActions?: boolean }>(), {
  appId: null,
  showActions: true,
});
const emit = defineEmits<{ completed: []; changed: [] }>();

const router = useRouter();
const message = useMessage();

const detail = ref<UtilApplicationDetail | null>(null);
const loading = ref(false);
const completing = ref(false);

const USE_TYPE_LABEL: Record<string, string> = { read: "查阅", borrow: "借阅", copy: "复制", certificate: "出具证明" };
const STATUS_LABEL: Record<string, string> = { processing: "办理中", completed: "已办结", cancelled: "已取消" };
const statusLabel = computed(() => STATUS_LABEL[detail.value?.status ?? ""] ?? detail.value?.status);
const statusTone = computed<"info" | "success" | "default">(() =>
  detail.value?.status === "processing" ? "info" : detail.value?.status === "completed" ? "success" : "default",
);

const infoFields = computed(() => {
  const a = detail.value;
  if (!a) return [];
  return [
    { label: "身份证号", value: a.id_card_no },
    { label: "性别", value: a.gender },
    { label: "联系电话", value: a.phone },
    { label: "工作单位", value: a.organization },
    { label: "利用方式", value: USE_TYPE_LABEL[a.use_type] ?? a.use_type },
    { label: "利用目的", value: a.purpose },
    { label: "经办人", value: a.handler_name },
  ];
});

async function reload() {
  if (!props.appId) { detail.value = null; return; }
  loading.value = true;
  try {
    detail.value = (await UtilizationAPI.get(props.appId)).data;
  } finally {
    loading.value = false;
  }
}

async function removeItem(itemId: string) {
  if (!props.appId) return;
  await UtilizationAPI.removeItem(props.appId, itemId);
  await reload();
  emit("changed");
}

async function complete() {
  if (!props.appId) return;
  completing.value = true;
  try {
    await UtilizationAPI.complete(props.appId);
    message.success("已办理完成");
    await reload();
    emit("completed");
  } finally {
    completing.value = false;
  }
}

function goProcess() {
  if (props.appId) router.push(`/archive/utilization/reading?app=${props.appId}`);
}
function openReader(archiveId: string) {
  window.open(`/archive/reader?id=${archiveId}`, "_blank", "noopener");
}

watch(() => props.appId, reload);
onMounted(reload);
defineExpose({ reload });
</script>
