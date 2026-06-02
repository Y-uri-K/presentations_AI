"use client";

import Link from "next/link";
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
    <header className="sticky top-0 z-10 border-b border-[var(--border)] bg-[var(--surface)]/85 backdrop-blur-sm">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-6">
        <Link href={ROUTES.dashboard} className="text-lg font-semibold text-[var(--foreground)]">
          AIDeck
        </Link>
        <div className="flex items-center gap-3">
          <Link
            href={ROUTES.profile}
            className="rounded-lg border border-[var(--border)] px-3 py-1.5 text-sm font-medium text-[var(--foreground)] transition-colors hover:border-[var(--primary)] hover:bg-[var(--surface-muted)]"
          >
            Личный кабинет
          </Link>
          <button
            type="button"
            onClick={handleLogout}
            className="rounded-lg border border-[var(--border)] px-3 py-1.5 text-sm font-medium text-[var(--muted)] transition-colors hover:border-[var(--primary)] hover:bg-[var(--surface-muted)] hover:text-[var(--foreground)]"
          >
            Выйти
          </button>
        </div>
      </div>
    </header>
  );
}
