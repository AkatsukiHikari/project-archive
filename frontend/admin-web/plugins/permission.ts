import { hasPermission } from "@/utils/permission";

/**
 * 全局自定义指令: v-permission
 * 自动拦截并移除无权限的 DOM 元素
 */
export default defineNuxtPlugin((nuxtApp) => {
  nuxtApp.vueApp.directive("permission", {
    mounted(el: HTMLElement, binding) {
      const { value } = binding;

      if (value) {
        const hasAuth = hasPermission(value);
        if (!hasAuth) {
          // 若无权限，直接将该DOM元素物理移除
          el.parentNode?.removeChild(el);
        }
      } else {
        console.warn(
          "使用 v-permission 必须提供权限标识! 示例: v-permission=\"['sys:user:add']\"",
        );
      }
    },
  });
});
