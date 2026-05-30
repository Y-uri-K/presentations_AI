import Link from "next/link";
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
      <aside className="relative lg:w-[44%] xl:w-[42%] overflow-hidden bg-gradient-to-br from-[#1d4ed8] via-[#2563eb] to-[#38bdf8] px-8 py-12 lg:px-14 lg:py-16 flex flex-col justify-center text-white">
        <div
          className="pointer-events-none absolute -top-24 -right-24 h-72 w-72 rounded-full bg-white/10 blur-3xl"
          aria-hidden
        />
        <div
          className="pointer-events-none absolute bottom-0 left-0 h-56 w-56 rounded-full bg-sky-300/20 blur-3xl"
          aria-hidden
        />

        <div className="relative z-10 max-w-md">
          <h1 className="text-3xl lg:text-4xl font-bold leading-tight tracking-tight">
            {title}
          </h1>
          <p className="mt-4 text-base lg:text-lg text-sky-100/90 leading-relaxed">{subtitle}</p>
        </div>

        <ul className="relative z-10 mt-10 lg:mt-8 space-y-3 text-sm text-sky-100/80 hidden sm:block">
          <li className="flex items-center gap-2">
            <span className="h-1.5 w-1.5 rounded-full bg-sky-200" />
            Создание презентаций с помощью ИИ на основе ваших шаблонов
          </li>
          <li className="flex items-center gap-2">
            <span className="h-1.5 w-1.5 rounded-full bg-sky-200" />
            Сохранение ваших шаблонов и использование их в будущем
          </li>
          <li className="flex items-center gap-2">
            <span className="h-1.5 w-1.5 rounded-full bg-sky-200" />
            Презентации под любую важную встречу
          </li>
        </ul>
      </aside>

      <main className="flex-1 flex items-center justify-center px-6 py-12 lg:px-12 bg-[var(--background)]">
        <div className="w-full max-w-md">
          <div className="rounded-2xl bg-surface p-8 sm:p-10 shadow-xl shadow-blue-900/5 ring-1 ring-slate-200/80">
            {children}
          </div>
          <p className="mt-6 text-center text-sm text-slate-500">{footer}</p>
        </div>
      </main>
      <LogoCorner />
    </div>
  );
}
