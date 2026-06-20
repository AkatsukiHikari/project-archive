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
    "@umoteam/umo-editor-nuxt",
  ],

  shadcn: {
    prefix: "",
    componentDir: "./components/ui",
  },

  // 编研在线文档编辑器（UmoEditor）默认中文
  umoEditor: {
    locale: "zh-CN",
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
        // 本地存储静态资源（编研图片/附件经 StorageAdapter 落到后端 /static）
        "/static": {
          target: "http://localhost:8000",
          changeOrigin: true,
        },
      },
    },
  },

  // 确保 vue-sonner 样式被构建
  build: {
    transpile: ["vue-sonner", "naive-ui", "@css-render/vue3-ssr"],
  },

  css: ["~/assets/css/daisy-semi-sync.css", "@umoteam/editor/style"],
});
