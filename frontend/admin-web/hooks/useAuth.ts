/**
 * OAuth2 PKCE 认证 Composable
 *
 * 核心流程：
 * 1. getLoginUrl() — 生成 PKCE code_verifier + 授权 URL
 * 2. handleCallback(code) — 用 code + code_verifier 换 tokens
 * 3. refreshToken() — 用 refresh_token 刷新 access_token
 * 4. logout() — 清除本地 token + 调后端 /oauth/logout
 */

import { useUserStore } from "@/stores/user";
import axios from "axios";

const OAUTH_CLIENT_ID = "admin-web";
const OAUTH_TOKEN_URL = "/oauth/token";
const OAUTH_LOGOUT_URL = "/oauth/logout";

// ─── PKCE 工具函数 ───

function generateCodeVerifier(): string {
  const array = new Uint8Array(32);
  crypto.getRandomValues(array);
  return base64UrlEncode(array);
}

async function generateCodeChallenge(verifier: string): Promise<string> {
  const encoder = new TextEncoder();
  const data = encoder.encode(verifier);
  const digest = await crypto.subtle.digest("SHA-256", data);
  return base64UrlEncode(new Uint8Array(digest));
}

function base64UrlEncode(buffer: Uint8Array): string {
  let binary = "";
  for (const byte of buffer) {
    binary += String.fromCharCode(byte);
  }
  return btoa(binary)
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/, "");
}

// ─── Composable ───

export function useAuth() {
  const userStore = useUserStore();

  /**
   * 构建 OAuth2 授权 URL 并存储 PKCE 参数。
   * 返回完整的重定向 URL，交由调用方决定如何重定向。
   */
  async function buildAuthorizeUrl(returnPath?: string): Promise<string> {
    const redirectUri = `${window.location.origin}/auth/callback`;
    const codeVerifier = generateCodeVerifier();
    const codeChallenge = await generateCodeChallenge(codeVerifier);

    // 生成 state 防 CSRF
    const state = crypto.randomUUID();

    // 存储 PKCE code_verifier + state（回调时需要）
    sessionStorage.setItem("pkce_code_verifier", codeVerifier);
    sessionStorage.setItem("oauth_redirect_uri", redirectUri);
    sessionStorage.setItem("oauth_state", state);
    // 存储原始页面路径
    if (returnPath) {
      sessionStorage.setItem("auth_return_path", returnPath);
    }

    // 构建授权 URL
    const params = new URLSearchParams({
      response_type: "code",
      client_id: OAUTH_CLIENT_ID,
      redirect_uri: redirectUri,
      code_challenge: codeChallenge,
      code_challenge_method: "S256",
      state,
    });

    return `/oauth/authorize?${params.toString()}`;
  }

  /**
   * 处理 OAuth2 回调：校验 state，然后用授权码换 tokens
   */
  async function handleCallback(
    code: string,
    returnedState?: string
  ): Promise<boolean> {
    const codeVerifier = sessionStorage.getItem("pkce_code_verifier");
    const redirectUri = sessionStorage.getItem("oauth_redirect_uri");
    const savedState = sessionStorage.getItem("oauth_state");

    if (!codeVerifier || !redirectUri) {
      console.error("Missing PKCE code_verifier or redirect_uri");
      return false;
    }

    // CSRF 防御：校验 state 参数
    if (returnedState !== undefined && returnedState !== savedState) {
      console.error("OAuth state mismatch — possible CSRF attack");
      return false;
    }

    try {
      // 用 form-urlencoded 发送（OAuth2 标准要求）
      const params = new URLSearchParams({
        grant_type: "authorization_code",
        code,
        code_verifier: codeVerifier,
        client_id: OAUTH_CLIENT_ID,
        redirect_uri: redirectUri,
      });

      const { data: res } = await axios.post(OAUTH_TOKEN_URL, params, {
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
      });

      if (res.code === 0 && res.data) {
        userStore.setToken(res.data.access_token);
        if (res.data.refresh_token) {
          localStorage.setItem("refresh_token", res.data.refresh_token);
        }
        // 换完 token 后立即拉取用户信息存入 Pinia
        await userStore.getUserInfo();
        // 清理 PKCE 临时数据
        sessionStorage.removeItem("pkce_code_verifier");
        sessionStorage.removeItem("oauth_redirect_uri");
        sessionStorage.removeItem("oauth_state");
        return true;
      }

      console.error("Token exchange failed:", res.message);
      return false;
    } catch (error) {
      console.error("Token exchange error:", error);
      return false;
    }
  }

  /**
   * 刷新 access_token
   */
  async function refreshAccessToken(): Promise<boolean> {
    const refreshToken = localStorage.getItem("refresh_token");
    if (!refreshToken) return false;

    try {
      const params = new URLSearchParams({
        grant_type: "refresh_token",
        refresh_token: refreshToken,
        client_id: OAUTH_CLIENT_ID,
      });

      const { data: res } = await axios.post(OAUTH_TOKEN_URL, params, {
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
      });

      if (res.code === 0 && res.data) {
        userStore.setToken(res.data.access_token);
        if (res.data.refresh_token) {
          localStorage.setItem("refresh_token", res.data.refresh_token);
        }
        return true;
      }
      return false;
    } catch {
      return false;
    }
  }

  /**
   * 注销：清除本地 token + 通知授权服务器销毁 session
   */
  async function logout() {
    try {
      await axios.post(OAUTH_LOGOUT_URL, null, {
        withCredentials: true,
      });
    } catch {
      // 即使注销请求失败也继续清除本地状态
    }

    userStore.resetToken();
    localStorage.removeItem("refresh_token");
    sessionStorage.removeItem("pkce_code_verifier");
    sessionStorage.removeItem("oauth_redirect_uri");
    sessionStorage.removeItem("oauth_state");
    sessionStorage.removeItem("auth_return_path");

    // 重定向到登录
    const url = await buildAuthorizeUrl("/");
    window.location.href = url;
  }

  return {
    buildAuthorizeUrl,
    handleCallback,
    refreshAccessToken,
    logout,
  };
}
