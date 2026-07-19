<template>
  <NModal
    :show="show"
    preset="dialog"
    title="转办（更换经办人）"
    positive-text="确认转办"
    negative-text="取消"
    :loading="submitting"
    @update:show="(v: boolean) => emit('update:show', v)"
    @positive-click="submit"
    @negative-click="emit('update:show', false)"
  >
    <div class="flex flex-col gap-3 py-2">
      <p class="text-[13px] m-0" style="color: var(--semi-color-text-2)">
        将该利用申请移交给其他工作人员继续办理，转办操作会记录审计留痕。
      </p>
      <NSelect
        v-model:value="targetId"
        :options="userOptions"
        :loading="loading"
        filterable
        placeholder="选择接手的工作人员"
      />
    </div>
  </NModal>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { NModal, NSelect, useMessage } from "naive-ui";
import { UserAPI, type User } from "@/api/iam";
import { UtilizationAPI } from "@/api/utilization";
import { useUserStore } from "@/stores/user";

const props = defineProps<{ show: boolean; appId: string | null }>();
const emit = defineEmits<{ (e: "update:show", v: boolean): void; (e: "done"): void }>();

const message = useMessage();
const userStore = useUserStore();

const users = ref<User[]>([]);
const loading = ref(false);
const submitting = ref(false);
const targetId = ref<string | null>(null);

const userOptions = computed(() =>
  users.value
    .filter((u) => u.id !== userStore.userInfo?.id)
    .map((u) => ({ label: u.full_name ? `${u.full_name}（${u.username}）` : u.username, value: u.id })),
);

watch(
  () => props.show,
  async (v) => {
    if (!v) return;
    targetId.value = null;
    loading.value = true;
    try {
      users.value = (await UserAPI.list()).data;
    } finally {
      loading.value = false;
    }
  },
);

async function submit() {
  if (!props.appId || !targetId.value) {
    message.warning("请选择接手的工作人员");
    return false;
  }
  submitting.value = true;
  try {
    const res = await UtilizationAPI.transfer(props.appId, targetId.value);
    if (res.code !== 0) {
      message.error(res.message);
      return false;
    }
    message.success("已转办");
    emit("done");
    emit("update:show", false);
    return true;
  } finally {
    submitting.value = false;
  }
}
</script>
