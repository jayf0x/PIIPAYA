const STORAGE_KEY = "deid:theme:v1";

export type Theme = "light" | "dark";

let current: Theme = "light";
const listeners = new Set<(theme: Theme) => void>();

export function getTheme(): Theme {
  return current;
}

export function setTheme(theme: Theme) {
  current = theme;
  if (typeof document !== "undefined") {
    document.documentElement.setAttribute("data-theme", theme);
  }
  if (typeof localStorage !== "undefined") {
    localStorage.setItem(STORAGE_KEY, theme);
  }
  for (const fn of listeners) fn(theme);
}

export function toggleTheme(): Theme {
  const next = current === "light" ? "dark" : "light";
  setTheme(next);
  return next;
}

export function initTheme() {
  if (typeof localStorage === "undefined") return;
  const stored = localStorage.getItem(STORAGE_KEY);
  if (stored === "dark" || stored === "light") {
    setTheme(stored);
  } else if (
    typeof window !== "undefined" &&
    window.matchMedia("(prefers-color-scheme: dark)").matches
  ) {
    setTheme("dark");
  } else {
    setTheme("light");
  }
}

export function onThemeChange(fn: (theme: Theme) => void): () => void {
  listeners.add(fn);
  return () => listeners.delete(fn);
}
