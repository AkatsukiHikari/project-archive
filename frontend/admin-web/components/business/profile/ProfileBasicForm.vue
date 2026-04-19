<template>
  <div
    class="rounded-2xl border shadow-sm"
    style="background:var(--semi-color-bg-0);border-color:var(--semi-color-border)"
  >
    <div class="px-6 py-4 border-b" style="border-color:var(--semi-color-border)">
      <h2 class="font-semibold" style="color:var(--semi-color-text-0)">基本资料</h2>
      <p class="text-xs mt-0.5" style="color:var(--semi-color-text-2)">管理您的个人信息与显示资料</p>
    </div>

    <div v-if="loading" class="flex justify-center items-center py-20">
      <NSpin size="large" />
    </div>

    <div v-else class="p-6 flex flex-col gap-5">
      <!-- 只读字段 -->
      <div class="grid grid-cols-2 gap-4">
        <div>
          <label class="field-label">用户名</label>
          <NInput :value="profile?.username" disabled />
        </div>
        <div>
          <label class="field-label">邮箱地址</label>
          <NInput :value="profile?.email" disabled />
        </div>
      </div>
      <!-- 可编辑字段 -->
      <div class="grid grid-cols-2 gap-4">
        <div>
          <label class="field-label">真实姓名</label>
          <NInput v-model:value="form.full_name" placeholder="请输入真实姓名" />
        </div>
        <div>
          <label class="field-label">手机号码</label>
          <NInput v-model:value="form.phone" placeholder="请输入手机号码" />
        </div>
      </div>
      <div>
        <label class="field-label">职位</label>
        <NInput v-model:value="form.job_title" placeholder="请输入职位名称" />
      </div>
      <div>
        <label class="field-label">个人简介</label>
        <NInput v-model:value="form.bio" type="textarea" :rows="3" placeholder="简单介绍一下自己..." />
      </div>

      <!-- 操作栏 -->
      <div
        class="flex items-center gap-3 pt-4 mt-1 border-t"
        style="border-color:var(--semi-color-border)"
      >
        <NButton type="primary" :loading="saving" @click="save">保存修改</NButton>
        <Transition name="fade">
          <span v-if="success" class="text-sm text-green-600 flex items-center gap-1">
            <Icon name="material-symbols:check-circle-outline" class="text-base" />保存成功
          </span>
        </Transition>
        <span v-if="error" class="text-sm text-red-500">{{ error }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from "vue";
import { NButton, NInput, NSpin, useMessage } from "naive-ui";
import { UserAPI, type User, type UserProfileUpdatePayload } from "@/api/iam";
import { useUserStore } from "@/stores/user";

const props = defineProps<{ profile: User | null; loading: boolean }>();
const emit = defineEmits<{ saved: [user: User] }>();

const message = useMessage();
const userStore = useUserStore();
const form = ref({ full_name: "", phone: "", job_title: "", bio: "" });
const saving = ref(false);
const success = ref(false);
const error = ref("");

watch(
  () => props.profile,
  (p) => {
    if (!p) return;
    form.value = {
      full_name: p.full_name || "",
      phone: p.phone || "",
      job_title: p.job_title || "",
      bio: p.bio || "",
    };
  },
  { immediate: true },
);

async function save() {
  saving.value = true;
  error.value = "";
  try {
    const payload: UserProfileUpdatePayload = {
      full_name: form.value.full_name || undefined,
      phone: form.value.phone || undefined,
      job_title: form.value.job_title || undefined,
      bio: form.value.bio || undefined,
    };
    const res = await UserAPI.updateProfile(payload);
    await userStore.getUserInfo();
    emit("saved", res.data);
    success.value = true;
    message.success("保存成功");
    setTimeout(() => (success.value = false), 3000);
  } catch (e) {
    error.value = e instanceof Error ? e.message : "保存失败";
    message.error(error.value);
  } finally {
    saving.value = false;
  }
}
</script>

<style scoped>
.field-label {
  display: block;
  font-size: 0.75rem;
  font-weight: 500;
  color: var(--semi-color-text-2);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 0.375rem;
}
.fade-enter-active, .fade-leave-active { transition: opacity 0.25s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
