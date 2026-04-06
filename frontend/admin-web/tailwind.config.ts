import type { Config } from "tailwindcss";
import daisyui from "daisyui";

export default <Config>{
  content: [
    "./components/**/*.{js,vue,ts}",
    "./layouts/**/*.vue",
    "./pages/**/*.vue",
    "./plugins/**/*.{js,ts}",
    "./app.vue",
    "./error.vue",
  ],
  theme: {
    extend: {
      fontFamily: {
        display: ["Inter", "system-ui", "sans-serif"],
      },
      boxShadow: {
        soft: "0 2px 8px -1px rgba(25, 120, 229, 0.08), 0 1px 4px -1px rgba(0, 0, 0, 0.04)",
        "soft-hover":
          "0 10px 15px -3px rgba(25, 120, 229, 0.12), 0 4px 6px -2px rgba(0, 0, 0, 0.05)",
        card: "0 1px 3px 0 rgba(0, 0, 0, 0.05), 0 1px 2px 0 rgba(0, 0, 0, 0.03)",
      },
      keyframes: {
        shimmer: {
          "100%": { transform: "translateX(100%)" },
        },
      },
    },
  },
  plugins: [daisyui],
  daisyui: {
    themes: [
      // light: 把 DaisyUI 默认的紫色 primary 替换成系统品牌蓝
      {
        light: {
          "color-scheme": "light",
          "primary": "#1978e5",
          "primary-content": "#ffffff",
          "secondary": "oklch(69.71% 0.329 342.55)",
          "secondary-content": "oklch(98.71% 0.0106 342.55)",
          "accent": "oklch(76.76% 0.184 183.61)",
          "neutral": "#2B3440",
          "neutral-content": "#D7DDE4",
          "base-100": "oklch(100% 0 0)",
          "base-200": "#F2F2F2",
          "base-300": "#E5E6E6",
          "base-content": "#1f2937",
        },
      },
      // coffee: primary 从暗橙改为暖金色，hero card 渐变不再泥棕
      {
        coffee: {
          "color-scheme": "dark",
          "primary": "#C8813A",
          "primary-content": "#ffffff",
          "secondary": "#263E3F",
          "accent": "#10576D",
          "neutral": "#120C12",
          "base-100": "#20161F",
          "base-content": "#c59f60",
          "info": "#8DCAC1",
          "success": "#9DB787",
          "warning": "#FFD25F",
          "error": "#FC9581",
        },
      },
      "dark",
      "aqua",
      "night",
      "valentine",
      "lemonade",
    ],
  },
};
