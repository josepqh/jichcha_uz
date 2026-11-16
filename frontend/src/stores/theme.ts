import { create } from "zustand";
import { persist } from "zustand/middleware";

export type ThemePreference = "system" | "light" | "dark";

interface ThemeState {
  theme: ThemePreference;
  cycle: () => void;
}

const ORDER: ThemePreference[] = ["system", "light", "dark"];

export const useThemeStore = create<ThemeState>()(
  persist(
    (set) => ({
      theme: "system",
      cycle: () => set((s) => ({ theme: ORDER[(ORDER.indexOf(s.theme) + 1) % ORDER.length] ?? "system" })),
    }),
    { name: "uv-theme", version: 1 },
  ),
);

export function applyTheme(theme: ThemePreference): void {
  const dark = theme === "dark" || (theme === "system" && window.matchMedia("(prefers-color-scheme: dark)").matches);
  document.documentElement.classList.toggle("dark", dark);
}
