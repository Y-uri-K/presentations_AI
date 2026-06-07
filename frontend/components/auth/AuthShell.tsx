import type { ReactNode } from "react";
import { LogoCorner } from "@/components/LogoCorner";

type AuthShellProps = {
  title: string;
  subtitle: string;
  children: ReactNode;
  footer: ReactNode;
};

export function AuthShell({ title, subtitle, children, footer }: AuthShellProps) {
  return (
    <div className="min-h-screen flex flex-col lg:flex-row">
      <aside className="relative flex flex-col justify-center overflow-hidden bg-gradient-to-br from-[var(--hero-from)] via-[var(--primary)] to-[var(--hero-to)] px-6 py-10 text-[var(--hero-text)] sm:px-8 sm:py-12 lg:w-[44%] lg:px-14 lg:py-16 xl:w-[42%]">
        <div
          className="pointer-events-none absolute -right-24 -top-24 h-72 w-72 rounded-full bg-[var(--hero-text)]/10 blur-3xl"
          aria-hidden
        />
        <div
          className="pointer-events-none absolute bottom-0 left-0 h-56 w-56 rounded-full bg-[var(--accent)]/20 blur-3xl"
          aria-hidden
        />

        <div className="relative z-10 max-w-md">
          <h1 className="text-3xl lg:text-4xl font-bold leading-tight tracking-tight">
            {title}
          </h1>
          <p className="mt-4 text-base leading-relaxed text-[var(--hero-muted)] lg:text-lg">{subtitle}</p>
        </div>

        <ul className="relative z-10 mt-10 hidden space-y-3 text-sm text-[var(--hero-muted)] sm:block lg:mt-8">
          <li className="flex items-center gap-2">
            <span className="h-1.5 w-1.5 rounded-full bg-[var(--accent)]" />
            Создание презентаций с помощью ИИ на основе ваших шаблонов
          </li>
          <li className="flex items-center gap-2">
            <span className="h-1.5 w-1.5 rounded-full bg-[var(--accent)]" />
            Сохранение ваших шаблонов и использование их в будущем
          </li>
          <li className="flex items-center gap-2">
            <span className="h-1.5 w-1.5 rounded-full bg-[var(--accent)]" />
            Презентации под любую важную встречу
          </li>
        </ul>
      </aside>

      <main className="flex flex-1 items-center justify-center bg-[var(--background)] px-4 py-10 sm:px-6 sm:py-12 lg:px-12">
        <div className="w-full max-w-md">
          <div className="rounded-2xl bg-[var(--surface)] p-6 shadow-xl shadow-[color:var(--primary)]/10 ring-1 ring-[var(--border)] sm:p-8 md:p-10">
            {children}
          </div>
          <p className="mt-6 text-center text-sm text-[var(--muted)]">{footer}</p>
        </div>
      </main>
      <LogoCorner />
    </div>
  );
}
