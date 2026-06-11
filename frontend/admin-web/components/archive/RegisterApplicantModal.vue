<template>
  <NModal :show="show" preset="card" :title="title" style="width: 560px; max-width: 95vw" :mask-closable="false" @update:show="(v) => emit('update:show', v)">
    <div class="flex flex-col gap-4">
      <div class="rounded-lg border border-dashed p-3 flex items-center gap-3" style="border-color:var(--semi-color-border)">
        <Icon name="heroicons:identification" class="w-5 h-5" style="color:oklch(var(--p))" />
        <span class="text-[12px]" style="color:var(--semi-color-text-2)">读卡器接入后可一键读取身份证；当前请手动录入</span>
      </div>
      <div class="grid grid-cols-2 gap-4">
        <LabeledField label="姓名" required><NInput v-model:value="form.applicant_name" placeholder="申请人姓名" /></LabeledField>
        <LabeledField label="身份证号"><NInput v-model:value="form.id_card_no" placeholder="身份证号" /></LabeledField>
        <LabeledField label="性别"><NSelect v-model:value="form.gender" :options="genderOptions" placeholder="性别" clearable /></LabeledField>
        <LabeledField label="联系电话"><NInput v-model:value="form.phone" placeholder="联系电话" /></LabeledField>
        <LabeledField label="工作单位" class="col-span-2"><NInput v-model:value="form.organization" placeholder="工作单位" /></LabeledField>
        <LabeledField label="利用目的" class="col-span-2"><NSelect v-model:value="form.purpose" :options="purposeOptions" placeholder="选择利用目的" clearable filterable tag /></LabeledField>
      </div>
    </div>
    <template #footer>
      <div class="flex justify-end gap-3">
        <NButton @click="emit('update:show', false)">取消</NButton>
        <NButton type="primary" :loading="saving" @click="submit">登记并选档</NButton>
      </div>
    </template>
  </NModal>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch, h } from "vue";
import { NModal, NInput, NSelect, NButton, useMessage } from "naive-ui";
import { UtilizationAPI } from "@/api/utilization";
import type { UtilApplication } from "@/api/utilization";
import { DictAPI, dictToOptions } from "@/api/dict";

const props = defineProps<{ show: boolean; useType: string }>();
const emit = defineEmits<{ "update:show": [v: boolean]; created: [app: UtilApplication] }>();

const message = useMessage();
const TITLE: Record<string, string> = { borrow: "登记借阅人", copy: "登记复制申请人", certificate: "登记证明申请人", read: "登记利用人" };
const title = computed(() => TITLE[props.useType] ?? "登记利用人");

const genderOptions = [{ label: "男", value: "男" }, { label: "女", value: "女" }];
const purposeOptions = ref<{ label: string; value: string }[]>([]);

const LabeledField = (p: { label: string; required?: boolean }, { slots }: { slots: { default?: () => unknown } }) =>
  h("div", { class: "flex flex-col gap-1" }, [
    h("span", { class: "text-sm font-medium" }, [p.label, p.required ? h("span", { class: "text-red-500 ml-0.5" }, "*") : null]),
    slots.default?.(),
  ]);

const saving = ref(false);
const form = reactive({ applicant_name: "", id_card_no: "", gender: null as string | null, phone: "", organization: "", purpose: null as string | null });

watch(() => props.show, (v) => {
  if (v) Object.assign(form, { applicant_name: "", id_card_no: "", gender: null, phone: "", organization: "", purpose: null });
});

async function submit() {
  if (!form.applicant_name.trim()) { message.warning("请填写申请人姓名"); return; }
  saving.value = true;
  try {
    const res = await UtilizationAPI.create({
      applicant_name: form.applicant_name.trim(), id_card_no: form.id_card_no.trim() || null,
      gender: form.gender, phone: form.phone.trim() || null, organization: form.organization.trim() || null,
      purpose: form.purpose, use_type: props.useType,
    });
    emit("update:show", false);
    emit("created", res.data);
  } finally {
    saving.value = false;
  }
}

DictAPI.listItems("LYMD").then((r) => { purposeOptions.value = dictToOptions(r.data); });
</script>
