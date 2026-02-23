/**
 * WebSocket 全局初始化插件 (client-only)
 *
 * - 用户已登录时自动建立 WebSocket 连接
 * - 注册全局事件监听：通知推送、工作台更新
 * - 使用 vue-sonner 显示新通知 toast
 */

import { useSocket } from "@/hooks/useSocket";
import { useNotificationStore } from "@/stores/notification";
import type { NotificationItem } from "@/api/notification";
import { toast } from "vue-sonner";

export default defineNuxtPlugin(() => {
  const socket = useSocket();
  const notificationStore = useNotificationStore();

  // ── 注册事件监听 ──

  // 1. 新通知推送
  socket.on("notification:new", (raw: unknown) => {
    const data = raw as NotificationItem;
    // 更新 store
    notificationStore.pushNotification(data);

    // 弹出 toast 通知
    const toastType =
      data.level === "error"
        ? "error"
        : data.level === "warning"
          ? "warning"
          : "info";

    toast[toastType](data.title, {
      description: data.content,
      duration: 5000,
    });
  });

  // 2. 连接成功日志
  socket.on("connected", (raw: unknown) => {
    const data = raw as { user_id: string };
    console.log("[WS Plugin] 已连接，用户:", data.user_id);
    // 连接成功后获取初始未读数量
    notificationStore.fetchUnreadCount();
  });

  // 3. 连接错误处理
  socket.on("error", (raw: unknown) => {
    const data = raw as { message: string };
    console.error("[WS Plugin] 服务端错误:", data.message);
  });

  // ── 初始化连接 ──
  socket.init();
});
