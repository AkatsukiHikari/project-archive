<template>
  <div
    class="rounded-2xl bg-[var(--semi-color-bg-0)] border border-[var(--semi-color-border)] shadow-sm"
  >
    <div class="px-6 py-4 border-b border-[var(--semi-color-border)]">
      <h2 class="font-semibold text-[var(--semi-color-text-0)]">安全管理</h2>
      <p class="text-xs text-[var(--semi-color-text-2)] mt-0.5">
        管理账户安全设置
      </p>
    </div>
    <div class="p-6 flex flex-col gap-4">
      <!-- 密码行 -->
      <div
        class="flex items-center justify-between p-4 rounded-xl border border-[var(--semi-color-border)] bg-[var(--semi-color-bg-1)]"
      >
        <div class="flex items-center gap-3">
          <div
            class="w-9 h-9 rounded-lg bg-[oklch(var(--p)/0.1)] flex items-center justify-center"
          >
            <Icon
              name="material-symbols:lock-outline"
              class="text-lg text-[oklch(var(--p))]"
            />
          </div>
          <div>
            <p class="text-sm font-medium text-[var(--semi-color-text-0)]">
              登录密码
            </p>
            <p class="text-xs text-[var(--semi-color-text-2)]">
              定期修改密码可提高账号安全性
            </p>
          </div>
        </div>
        <Button type="primary" theme="light" @click="modalVisible = true"
          >修改密码</Button
        >
      </div>
      <!-- 最近登录行 -->
      <div
        class="flex items-center justify-between p-4 rounded-xl border border-[var(--semi-color-border)] bg-[var(--semi-color-bg-1)]"
      >
        <div class="flex items-center gap-3">
          <div
            class="w-9 h-9 rounded-lg bg-green-500/10 flex items-center justify-center"
          >
            <Icon
              name="material-symbols:history"
              class="text-lg text-green-600"
            />
          </div>
          <div>
            <p class="text-sm font-medium text-[var(--semi-color-text-0)]">
              最近登录
            </p>
            <p class="text-xs text-[var(--semi-color-text-2)]">
              {{ lastLoginDisplay }}
            </p>
          </div>
        </div>
        <Tag color="green">安全</Tag>
      </div>
    </div>

    <!-- 密码弹窗 -->
    <Modal
      v-model:visible="modalVisible"
      title="修改密码"
      :confirm-loading="saving"
      @ok="save"
      @cancel="reset"
    >
      <div class="flex flex-col gap-4 mt-4">
        <div>
          <label class="field-label"
            >当前密码 <span class="text-red-500">*</span></label
          >
          <Input
            v-model="form.old_password"
            type="password"
            placeholder="请输入当前密码"
          />
        </div>
        <div>
          <label class="field-label"
            >新密码 <span class="text-red-500">*</span></label
          >
          <Input
            v-model="form.new_password"
            type="password"
            placeholder="至少 8 位，含字母和数字"
          />
        </div>
        <div>
          <label class="field-label"
            >确认新密码 <span class="text-red-500">*</span></label
          >
          <Input
            v-model="form.confirm"
            type="password"
            placeholder="再次输入新密码"
          />
        </div>
        <p
          v-if="formError"
          class="text-sm text-red-500 flex items-center gap-1"
        >
          <Icon name="material-symbols:error-outline" class="text-base" />{{
            formError
          }}
        </p>
      </div>
    </Modal>
  </div>
</template>

<script setup lang="ts">
import { ref } from "vue";
import { Button, Input, Modal, Tag, Toast } from "@kousum/semi-ui-vue";
import { UserAPI } from "@/api/iam";

defineProps<{ lastLoginDisplay: string }>();

const modalVisible = ref(false);
const saving = ref(false);
const formError = ref("");
const form = ref({ old_password: "", new_password: "", confirm: "" });

function reset() {
  modalVisible.value = false;
  formError.value = "";
  form.value = { old_password: "", new_password: "", confirm: "" };
}

async function save() {
  formError.value = "";
  if (!form.value.old_password || !form.value.new_password) {
    formError.value = "请填写全部密码字段";
    return;
  }
  if (form.value.new_password !== form.value.confirm) {
    formError.value = "两次输入的新密码不一致";
    return;
  }
  if (form.value.new_password.length < 8) {
    formError.value = "新密码不得少于 8 位";
    return;
  }
  saving.value = true;
  try {
    await UserAPI.updatePassword({
      old_password: form.value.old_password,
      new_password: form.value.new_password,
    });
    Toast.success("密码修改成功");
    reset();
  } catch (e) {
    formError.value = e instanceof Error ? e.message : "密码修改失败";
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
</style>
