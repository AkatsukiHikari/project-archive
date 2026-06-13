<template>
  <NModal
    :show="show"
    preset="card"
    :title="`批量修改（${selectedIds.length} 条）`"
    style="width: 520px; max-width: 95vw"
    :mask-closable="false"
    @update:show="(v: boolean) => emit('update:show', v)"
  >
    <div class="flex flex-col gap-3">
      <p class="text-[12px]" style="color:var(--semi-color-text-2)">
        勾选要修改的字段，未勾选的字段保持原值不动。
      </p>

      <div
        v-for="field in fields"
        :key="field.key"
        class="flex items-center gap-3 px-3 py-2 rounded-lg"
        style="background:var(--semi-color-fill-0)"
      >
        <NCheckbox v-model:checked="field.enabled" class="w-24 shrink-0">
          {{ field.label }}
        </NCheckbox>
        <div class="flex-1">
          <NSelect
            v-if="field.key === 'MJ'"
            v-model:value="form.MJ"
            :options="mjOptions"
            :disabled="!field.enabled"
            size="small"
          />
          <NSelect
            v-else-if="field.key === 'BGQX'"
            v-model:value="form.BGQX"
            :options="bgqxOptions"
            :disabled="!field.enabled"
            size="small"
          />
          <NInputNumber
            v-else-if="field.key === 'ND'"
            v-model:value="form.ND"
            :disabled="!field.enabled"
            size="small"
            class="w-full"
            placeholder="年度"
          />
          <NInput
            v-else-if="field.key === 'WJRQ'"
            v-model:value="form.WJRQ"
            :disabled="!field.enabled"
            size="small"
            placeholder="YYYY-MM-DD"
          />
          <NInput
            v-else
            v-model:value="form.RZZ"
            :disabled="!field.enabled"
            size="small"
            placeholder="责任者"
          />
        </div>
      </div>
    </div>

    <template #footer>
      <div class="flex justify-end gap-3">
        <NButton @click="emit('update:show', false)">取消</NButton>
        <NButton type="primary" :loading="saving" @click="submit">应用修改</NButton>
      </div>
    </template>
  </NModal>
</template>

<script setup lang="ts">
import { reactive, ref, watch } from "vue";
import { NButton, NCheckbox, NInput, NInputNumber, NModal, NSelect, useMessage } from "naive-ui";
import { OrganizeAPI } from "@/api/repository";
import type { BatchUpdatePayload } from "@/api/repository";

const props = defineProps<{ show: boolean; selectedIds: string[] }>();
const emit = defineEmits<{ "update:show": [boolean]; done: [] }>();

const message = useMessage();
const saving = ref(false);

const mjOptions = [
  { label: "无", value: "无" }, { label: "秘密", value: "秘密" },
  { label: "机密", value: "机密" }, { label: "绝密", value: "绝密" },
];
const bgqxOptions = [
  { label: "永久", value: "permanent" },
  { label: "长期", value: "long" },
  { label: "短期", value: "short" },
];

const fields = reactive([
  { key: "MJ", label: "密级", enabled: false },
  { key: "BGQX", label: "保管期限", enabled: false },
  { key: "RZZ", label: "责任者", enabled: false },
  { key: "ND", label: "年度", enabled: false },
  { key: "WJRQ", label: "文件日期", enabled: false },
]);

const form = reactive({
  MJ: "无",
  BGQX: "long",
  RZZ: "",
  ND: null as number | null,
  WJRQ: "",
});

watch(() => props.show, (v) => {
  if (v) fields.forEach((f) => { f.enabled = false; });
});

async function submit() {
  const enabled = fields.filter((f) => f.enabled);
  if (!enabled.length) return message.warning("请勾选至少一个要修改的字段");

  const payload: BatchUpdatePayload = { ids: props.selectedIds };
  for (const f of enabled) {
    if (f.key === "MJ") payload.MJ = form.MJ;
    if (f.key === "BGQX") payload.BGQX = form.BGQX;
    if (f.key === "RZZ") payload.RZZ = form.RZZ || undefined;
    if (f.key === "ND") payload.ND = form.ND ?? undefined;
    if (f.key === "WJRQ") payload.WJRQ = form.WJRQ || undefined;
  }

  saving.value = true;
  try {
    const res = await OrganizeAPI.batchUpdate(payload);
    if (res.code === 0) {
      message.success(`已更新 ${res.data.updated} 条档案`);
      emit("update:show", false);
      emit("done");
    } else {
      message.error(res.message);
    }
  } finally {
    saving.value = false;
  }
}
</script>
