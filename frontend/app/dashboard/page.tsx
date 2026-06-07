import type { Metadata } from "next";
import { AppHeader } from "@/components/dashboard/AppHeader";
import { DashboardClient } from "@/components/dashboard/DashboardClient";
import { LogoCorner } from "@/components/LogoCorner";

export const metadata: Metadata = {
  title: "Кабинет — AIDeck",
  description: "Личный кабинет AIDeck",
};

export default function DashboardPage() {
  return (
    <div className="min-h-screen bg-[var(--background)]">
      <AppHeader />

      <main className="mx-auto max-w-6xl px-4 py-8 sm:px-6 sm:py-12">
        <div className="rounded-2xl bg-gradient-to-br from-[var(--hero-from)] to-[var(--hero-to)] p-6 text-[var(--hero-text)] shadow-lg shadow-[color:var(--primary)]/15 sm:p-8 md:p-10">
          <p className="text-sm font-medium text-[var(--hero-muted)]">Добро пожаловать</p>
          <h1 className="mt-2 text-2xl sm:text-3xl font-bold tracking-tight">
            Ваш рабочий стол
          </h1>
          <p className="mt-3 max-w-xl leading-relaxed text-[var(--hero-muted)]">
            Опишите тему презентации, приложите материалы Word, PDF, Markdown или TXT и выберите
            шаблон оформления.
          </p>
        </div>

        <DashboardClient />
      </main>
      <LogoCorner />
    </div>
  );
}
