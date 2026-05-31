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

      <main className="mx-auto max-w-6xl px-6 py-12">
        <div className="rounded-2xl bg-gradient-to-br from-[var(--primary)] to-[var(--accent)] p-8 sm:p-10 text-white shadow-lg shadow-blue-500/20">
          <p className="text-sm font-medium text-sky-100">Добро пожаловать</p>
          <h1 className="mt-2 text-2xl sm:text-3xl font-bold tracking-tight">
            Ваш рабочий стол
          </h1>
          <p className="mt-3 max-w-xl text-sky-50/90 leading-relaxed">
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
