/**
 * WebSocket Composable
 *
 * 基于 @vueuse/core 的 useWebSocket 封装全局 WebSocket 连接管理。
 *
 * 特性：
 * - JWT Token 认证（通过 query param）
 * - 自动重连（最大 5 次，间隔 3s）
 * - 心跳检测（每 30s 发送 ping）
 * - 事件注册 / 分发机制：on(event, handler) / off(event, handler)
 */

import { useWebSocket } from "@vueuse/core";
import { useUserStore } from "@/stores/user";
import { watch } from "vue";

// ── 事件系统 ──
type EventHandler = (data: unknown) => void;
const eventHandlers = new Map<string, Set<EventHandler>>();

// ── WebSocket 实例状态（模块级单例） ──
let wsInstance: ReturnType<typeof useWebSocket> | null = null;
let watcherStop: (() => void) | null = null;

/**
 * 全局 WebSocket Composable
 */
export function useSocket() {
  const userStore = useUserStore();

  /**
   * 注册事件监听
   */
  function on(event: string, handler: EventHandler) {
    if (!eventHandlers.has(event)) {
      eventHandlers.set(event, new Set());
    }
    eventHandlers.get(event)!.add(handler);
  }

  /**
   * 移除事件监听
   */
  function off(event: string, handler: EventHandler) {
    eventHandlers.get(event)?.delete(handler);
  }

  /**
   * 分发消息到已注册的处理器
   */
  function dispatch(event: string, data: unknown) {
    const handlers = eventHandlers.get(event);
    if (handlers) {
      handlers.forEach((handler) => {
        try {
          handler(data);
        } catch (err) {
          console.error(`[WS] 事件 "${event}" 处理器执行异常:`, err);
        }
      });
    }
  }

  /**
   * 建立 WebSocket 连接
   */
  function connect() {
    // 如果已有连接，先断开
    if (wsInstance) {
      disconnect();
    }

    const token = userStore.token;
    if (!token) {
      console.warn("[WS] 未登录，跳过 WebSocket 连接");
      return;
    }

    // 构造 WebSocket URL
    // 【主流最佳实践】：在本地开发环境 (Dev) 直连后端 WebSocket 端口，彻底绕过 Vite/Nuxt 的代理层。
    // 这解决了 Vite HMR 与外部 WebSocket 代理抢占造成的 dev server 崩溃问题。
    // 生产环境中（由于打成了同域名的静态包或由 Nginx 统一反代），则正常使用当前域名。
    const isDev = import.meta.env.DEV;
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const host = isDev ? "localhost:8000" : window.location.host;
    const wsUrl = `${isDev ? "ws:" : protocol}//${host}/ws?token=${encodeURIComponent(token)}`;

    wsInstance = useWebSocket(wsUrl, {
      // ── 自动重连 ──
      autoReconnect: {
        retries: 5,
        delay: 3000,
      },

      // ── 心跳检测 ──
      heartbeat: {
        message: JSON.stringify({ event: "ping" }),
        interval: 30000,
        pongTimeout: 5000,
      },

      // ── 消息处理 ──
      onMessage: (_ws, messageEvent) => {
        try {
          const msg = JSON.parse(messageEvent.data);
          if (msg.event) {
            dispatch(msg.event, msg.data);
          }
        } catch {
          // 非 JSON 消息，忽略
        }
      },

      onConnected: () => {
        console.log("[WS] 连接已建立");
      },

      onDisconnected: (_ws, event) => {
        console.log("[WS] 连接已断开", event?.reason || "");
      },

      onError: (_ws, event) => {
        console.error("[WS] 连接错误", event);
      },
    });

    return wsInstance;
  }

  /**
   * 断开 WebSocket 连接
   */
  function disconnect() {
    if (wsInstance) {
      wsInstance.close();
      wsInstance = null;
    }
  }

  /**
   * 初始化 — 启动连接并监听 token 变化
   *
   * 应在 Nuxt plugin 中调用一次。
   */
  function init() {
    if (userStore.token) {
      connect();
    }

    // 监听 token 变化：token 清空时断开，token 出现时连接
    watcherStop = watch(
      () => userStore.token,
      (newToken, oldToken) => {
        if (!newToken && oldToken) {
          // 登出
          disconnect();
        } else if (newToken && !oldToken) {
          // 登入
          connect();
        }
      },
    );
  }

  /**
   * 销毁 — 断开连接并移除 watcher
   */
  function destroy() {
    disconnect();
    if (watcherStop) {
      watcherStop();
      watcherStop = null;
    }
    eventHandlers.clear();
  }

  // ── 导出 ──
  return {
    connect,
    disconnect,
    init,
    destroy,
    on,
    off,
    get isConnected() {
      return wsInstance?.status.value === "OPEN";
    },
  };
}
