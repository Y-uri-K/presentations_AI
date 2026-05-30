import type { Metadata } from "next";
import { AppHeader } from "@/components/dashboard/AppHeader";
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
            Здесь появятся ваши презентации и инструменты генерации. Страница-заглушка для
            переадресации после входа.
          </p>
        </div>

        <div className="mt-8 grid gap-4 sm:grid-cols-3">
          {[
            { title: "Мои презентации", desc: "Список и управление проектами" },
            { title: "Новая презентация", desc: "Создание с помощью ИИ" },
            { title: "Шаблоны", desc: "Ваши сохранённые шаблоны" },
          ].map((item) => (
            <div
              key={item.title}
              className="rounded-xl border border-dashed border-slate-300 bg-white p-6 text-slate-400"
            >
              <h2 className="font-semibold text-slate-700">{item.title}</h2>
              <p className="mt-1 text-sm">{item.desc}</p>
              <p className="mt-4 text-xs uppercase tracking-wide">Скоро</p>
            </div>
          ))}
        </div>
      </main>
      <LogoCorner />
    </div>
  );
}
