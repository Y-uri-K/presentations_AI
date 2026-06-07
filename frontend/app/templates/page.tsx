import type { Metadata } from "next";

import { AppHeader } from "@/components/dashboard/AppHeader";
import { LogoCorner } from "@/components/LogoCorner";
import { PublicTemplatesClient } from "@/components/templates/PublicTemplatesClient";

export const metadata: Metadata = {
  title: "Шаблоны — AIDeck",
  description: "Публичные шаблоны презентаций AIDeck",
};

export default function TemplatesPage() {
  return (
    <div className="min-h-screen bg-[var(--background)]">
      <AppHeader />

      <main className="mx-auto max-w-6xl px-4 py-8 sm:px-6 sm:py-12">
        <div className="mb-8 rounded-2xl bg-gradient-to-br from-[var(--hero-from)] to-[var(--hero-to)] p-6 text-[var(--hero-text)] shadow-lg shadow-[color:var(--primary)]/15 sm:p-8 md:p-10">
          <p className="text-sm font-medium text-[var(--hero-muted)]">Каталог сообщества</p>
          <h1 className="mt-2 text-2xl font-bold tracking-tight sm:text-3xl">
            Шаблоны презентаций
          </h1>
          <p className="mt-3 max-w-2xl leading-relaxed text-[var(--hero-muted)]">
            Загружайте публичные PPTX/PDF-шаблоны, оценивайте работы других пользователей,
            ищите подходящий стиль и скачивайте понравившиеся варианты.
          </p>
        </div>

        <PublicTemplatesClient />
      </main>
      <LogoCorner />
    </div>
  );
}
