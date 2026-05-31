"use client";

import { CreatePresentationPanel } from "@/components/dashboard/CreatePresentationPanel";
import { TemplateSelectionProvider } from "@/components/dashboard/TemplateSelectionContext";
import { TemplatesPanel } from "@/components/dashboard/TemplatesPanel";

const PLACEHOLDER_CARDS = [
  { title: "Мои презентации", desc: "Список и управление проектами" },
] as const;

export function DashboardClient() {
  return (
    <TemplateSelectionProvider>
      <div className="mt-8">
        <CreatePresentationPanel />
      </div>

      <div className="mt-8 grid gap-4 sm:grid-cols-2">
        {PLACEHOLDER_CARDS.map((item) => (
          <div
            key={item.title}
            className="rounded-xl border border-dashed border-slate-300 bg-white p-6 text-slate-400"
          >
            <h2 className="font-semibold text-slate-700">{item.title}</h2>
            <p className="mt-1 text-sm">{item.desc}</p>
            <p className="mt-4 text-xs uppercase tracking-wide">Скоро</p>
          </div>
        ))}
        <TemplatesPanel />
      </div>
    </TemplateSelectionProvider>
  );
}
