/**
 * 通知状态管理 Store
 *
 * - 维护未读通知数量和最近的通知列表
 * - 通过 WebSocket 接收实时通知推送
 * - 提供 REST API 操作（获取未读数、标记已读等）
 */

import { defineStore } from "pinia";
import type { NotificationItem } from "@/api/notification";
import { getUnreadCount } from "@/api/notification";

export const useNotificationStore = defineStore("notification", {
  state: () => ({
    /** 未读通知数量 */
    unreadCount: 0,
    /** 最近的实时通知（WebSocket 推送，仅保留最近 50 条） */
    recentNotifications: [] as NotificationItem[],
  }),

  actions: {
    /**
     * 从后端 REST API 获取当前未读数量
     */
    async fetchUnreadCount() {
      try {
        this.unreadCount = await getUnreadCount();
      } catch (err) {
        console.error("[NotificationStore] 获取未读数量失败:", err);
      }
    },

    /**
     * WebSocket 推送新通知时调用
     */
    pushNotification(notification: NotificationItem) {
      // 添加到最近通知队列头部
      this.recentNotifications.unshift(notification);

      // 限制队列长度为 50
      if (this.recentNotifications.length > 50) {
        this.recentNotifications = this.recentNotifications.slice(0, 50);
      }

      // 未读数 +1
      this.unreadCount++;
    },

    /**
     * 标记已读后调用
     */
    decrementUnread(count: number = 1) {
      this.unreadCount = Math.max(0, this.unreadCount - count);
    },

    /**
     * 全部标记已读后调用
     */
    clearUnread() {
      this.unreadCount = 0;
    },

    /**
     * 从最近列表中移除指定通知
     */
    removeNotification(id: string) {
      this.recentNotifications = this.recentNotifications.filter(
        (n) => n.id !== id,
      );
    },
  },
});
