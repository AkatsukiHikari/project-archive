/**
 * 通知 API 服务
 *
 * 对接后端 /api/v1/notifications 端点
 */

import { service as http } from "@/utils/axios/service";

export interface NotificationItem {
  id: string;
  title: string;
  content: string;
  type: "system" | "todo" | "message";
  level: "info" | "warning" | "error";
  is_read: boolean;
  read_time: string | null;
  create_time: string;
  user_id: string;
}

export interface NotificationPage {
  items: NotificationItem[];
  total: number;
  page: number;
  page_size: number;
}

export interface UnreadCount {
  count: number;
}

/**
 * 获取当前用户的通知（分页）
 */
export async function getNotifications(params?: {
  type?: string;
  page?: number;
  page_size?: number;
}): Promise<NotificationPage> {
  const res: any = await http.get("/notifications", { params });
  return res.data;
}

/**
 * 获取未读通知数量
 */
export async function getUnreadCount(): Promise<number> {
  const res: any = await http.get("/notifications/unread-count");
  return res.data.count;
}

/**
 * 标记单条通知为已读
 */
export async function markNotificationRead(id: string): Promise<void> {
  await http.put(`/notifications/${id}/read`);
}

/**
 * 全部标记为已读
 */
export async function markAllNotificationsRead(): Promise<void> {
  await http.put("/notifications/read-all");
}

/**
 * 删除通知
 */
export async function deleteNotification(id: string): Promise<void> {
  await http.delete(`/notifications/${id}`);
}
