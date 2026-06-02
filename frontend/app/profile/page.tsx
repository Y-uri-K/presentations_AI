import type { Metadata } from "next";

import { AppHeader } from "@/components/dashboard/AppHeader";
import { LogoCorner } from "@/components/LogoCorner";
import { ProfileClient } from "@/components/profile/ProfileClient";

export const metadata: Metadata = {
  title: "Профиль — AIDeck",
  description: "Личный кабинет пользователя AIDeck",
};

export default function ProfilePage() {
  return (
    <div className="min-h-screen bg-[var(--background)]">
      <AppHeader />

      <main className="mx-auto max-w-6xl px-6 py-12">
        <div className="mb-8 rounded-2xl bg-gradient-to-br from-[var(--hero-from)] to-[var(--hero-to)] p-8 text-[var(--hero-text)] shadow-lg shadow-[color:var(--primary)]/15 sm:p-10">
          <p className="text-sm font-medium text-[var(--hero-muted)]">Личный кабинет</p>
          <h1 className="mt-2 text-2xl font-bold tracking-tight sm:text-3xl">
            Управление профилем
          </h1>
          <p className="mt-3 max-w-xl leading-relaxed text-[var(--hero-muted)]">
            Обновите фотографию, username, тему интерфейса и настройки аккаунта.
          </p>
        </div>

        <ProfileClient />
      </main>
      <LogoCorner />
    </div>
  );
}
