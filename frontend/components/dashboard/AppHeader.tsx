"use client";

import { useRouter } from "next/navigation";

import { ROUTES } from "@/lib/auth/constants";
import { clearTokens } from "@/lib/auth/token";

export function AppHeader() {
  const router = useRouter();

  function handleLogout() {
    clearTokens();
    router.push(ROUTES.login);
  }

  return (
    <header className="border-b border-slate-200/80 bg-white/80 backdrop-blur-sm sticky top-0 z-10">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-6">
        <span className="text-lg font-semibold text-slate-900">AIDeck</span>
        <div className="flex items-center gap-3">
          <span className="hidden sm:inline text-sm text-slate-500">Личный кабинет</span>
          <button
            type="button"
            onClick={handleLogout}
            className="rounded-lg border border-slate-200 px-3 py-1.5 text-sm font-medium text-slate-700 transition-colors hover:border-sky-200 hover:bg-sky-50"
          >
            Выйти
          </button>
        </div>
      </div>
    </header>
  );
}
