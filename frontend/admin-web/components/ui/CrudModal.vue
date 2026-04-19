<template>
  <NModal
    :show="visible"
    preset="card"
    :title="title"
    :style="{ width: width + 'px' }"
    :mask-closable="false"
    :close-on-esc="false"
    @update:show="(v) => !v && emit('update:visible', false)"
  >
    <div class="pt-1">
      <slot />
    </div>
    <template #footer>
      <div class="flex justify-end gap-2">
        <NButton @click="emit('update:visible', false)">取消</NButton>
        <NButton type="primary" :loading="loading" @click="emit('confirm')">
          确认
        </NButton>
      </div>
    </template>
  </NModal>
</template>

<script setup lang="ts">
import { NModal, NButton } from "naive-ui";

/**
 * CrudModal —— 统一新增 / 编辑弹窗容器
 *
 * 使用示例：
 *   <CrudModal v-model:visible="visible" :title :loading @confirm="submitForm">
 *     <NForm ref="formRef" :model="formData" @submit.prevent>
 *       ...
 *     </NForm>
 *   </CrudModal>
 */
withDefaults(
  defineProps<{
    visible: boolean;
    title: string;
    loading?: boolean;
    width?: number;
  }>(),
  {
    loading: false,
    width: 520,
  },
);

const emit = defineEmits<{
  (e: "update:visible", val: boolean): void;
  (e: "confirm"): void;
}>();
</script>
