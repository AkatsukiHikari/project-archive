// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  // 切换为 SPA 模式（Single Page Application）
  ssr: false,

  compatibilityDate: "2025-07-15",
  devtools: { enabled: true },

  modules: [
    "@nuxtjs/tailwindcss",
    "@pinia/nuxt",
    "@nuxt/icon",
    "@nuxt/eslint",
    "@nuxt/fonts",
    "@nuxt/image",
    "shadcn-nuxt",
  ],

  shadcn: {
    prefix: "",
    componentDir: "./components/ui",
  },

  pinia: {
    storesDirs: ["./stores/**"],
  },

  components: [
    {
      path: "~/components",
      ignore: ["**/index.ts"],
    },
  ],

  runtimeConfig: {
    public: {
      apiBase: "/api/v1",
    },
  },

  // 开发环境 HTTP 请求使用 Vite 代理（必须用 Vite 代理，否则 /oauth/login HTML 会被 Vite SPA 拦截报错 404）
  vite: {
    server: {
      proxy: {
        "/api": {
          target: "http://localhost:8000",
          changeOrigin: true,
          autoRewrite: true,
        },
        "/oauth": {
          target: "http://localhost:8000",
          changeOrigin: true,
          autoRewrite: true,
        },
      },
    },
  },

  // 确保 vue-sonner 样式被构建
  build: {
    transpile: ["vue-sonner", "naive-ui", "@css-render/vue3-ssr"],
  },

  css: ["~/assets/css/daisy-semi-sync.css"],
});
