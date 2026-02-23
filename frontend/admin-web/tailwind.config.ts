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
      colors: {
        primary: "#1978e5",
        "primary-hover": "#1462bd",
      },
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
    themes: ["light", "dark", "cupcake", "nord", "business", "dracula"],
  },
};
