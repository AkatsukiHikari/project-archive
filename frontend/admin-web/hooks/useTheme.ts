/**
 * DaisyUI 主题切换 Hook
 *
 * 功能：
 * - 提供可选主题列表（含预览色）
 * - 在 <html> 元素上设置 data-theme 属性
 * - 持久化到 localStorage，刷新后自动恢复
 */

export interface ThemeOption {
  name: string;
  label: string;
  colors: string[]; // 预览色块
}

const STORAGE_KEY = "app-theme";

const themes: ThemeOption[] = [
  {
    name: "light",
    label: "明亮",
    colors: ["#570df8", "#f000b8", "#37cdbe", "#3d4451"],
  },
  {
    name: "dark",
    label: "暗黑",
    colors: ["#661ae6", "#d926a9", "#1fb2a6", "#191d24"],
  },
  {
    name: "cupcake",
    label: "柔粉",
    colors: ["#65c3c8", "#ef9fbc", "#eeaf3a", "#291334"],
  },
  {
    name: "nord",
    label: "北欧",
    colors: ["#5e81ac", "#bf616a", "#ebcb8b", "#2e3440"],
  },
  {
    name: "business",
    label: "商务",
    colors: ["#1c4f82", "#7c909a", "#ea6947", "#23282e"],
  },
  {
    name: "dracula",
    label: "暗紫",
    colors: ["#ff79c6", "#bd93f9", "#ffb86c", "#282a36"],
  },
];

export function useTheme() {
  const currentTheme = useState<string>("app-theme", () => {
    if (import.meta.client) {
      return localStorage.getItem(STORAGE_KEY) || "light";
    }
    return "light";
  });

  /** 应用主题到 DOM */
  function applyTheme(theme: string) {
    if (import.meta.client) {
      // 1. 设置 DaisyUI 主题
      document.documentElement.setAttribute("data-theme", theme);

      // 2. 同步 Semi UI 主题
      // 判定哪些 DaisyUI 主题属于暗黑偏好，这里包含 dark, business, dracula, nord(部分偏暗)
      const darkThemes = ["dark", "business", "dracula"];
      if (darkThemes.includes(theme)) {
        document.body.setAttribute("theme-mode", "dark");
      } else {
        document.body.removeAttribute("theme-mode");
      }
    }
  }

  /** 切换主题 */
  function setTheme(theme: string) {
    currentTheme.value = theme;
    applyTheme(theme);
    if (import.meta.client) {
      localStorage.setItem(STORAGE_KEY, theme);
    }
  }

  /** 初始化（在 onMounted 中调用） */
  function initTheme() {
    applyTheme(currentTheme.value);
  }

  return {
    currentTheme,
    themes,
    setTheme,
    initTheme,
  };
}
