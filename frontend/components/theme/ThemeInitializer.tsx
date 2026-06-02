"use client";

import { useEffect } from "react";

export const THEME_STORAGE_KEY = "aideck_theme";
export type AppTheme = "light" | "dark";

export function applyAppTheme(theme: AppTheme) {
  document.documentElement.dataset.theme = theme;
  document.documentElement.classList.toggle("dark", theme === "dark");
  localStorage.setItem(THEME_STORAGE_KEY, theme);
}

export function getSavedAppTheme(): AppTheme {
  const saved = localStorage.getItem(THEME_STORAGE_KEY);
  return saved === "dark" ? "dark" : "light";
}

export function ThemeInitializer() {
  useEffect(() => {
    applyAppTheme(getSavedAppTheme());
  }, []);

  return null;
}
