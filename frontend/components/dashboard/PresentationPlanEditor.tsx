"use client";

import { useMemo, useState } from "react";

import { parseOutline } from "@/lib/outline/parseOutline";
import { MAX_PRESENTATION_SLIDES } from "@/lib/presentation/limits";

type PlanViewMode = "preview" | "edit";

type PresentationPlanEditorProps = {
  outline: string;
  onOutlineChange: (value: string) => void;
  onSave: () => void | Promise<void>;
  isDirty: boolean;
  isSaving: boolean;
  disabled?: boolean;
};

export function PresentationPlanEditor({
  outline,
  onOutlineChange,
  onSave,
  isDirty,
  isSaving,
  disabled = false,
}: PresentationPlanEditorProps) {
  const [mode, setMode] = useState<PlanViewMode>("preview");
  const slides = useMemo(() => parseOutline(outline), [outline]);
  const overSlideLimit = slides.length > MAX_PRESENTATION_SLIDES;

  return (
    <div className="rounded-2xl border border-slate-200 bg-white shadow-sm overflow-hidden">
      <div className="flex flex-col gap-3 border-b border-slate-100 bg-gradient-to-r from-slate-50 to-sky-50/80 px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h3 className="text-base font-semibold text-slate-900">План презентации</h3>
          <p className="text-xs text-slate-500 mt-0.5">
            {slides.length} {slidesLabel(slides.length)} (макс. {MAX_PRESENTATION_SLIDES})
            {isDirty ? " · есть несохранённые изменения" : null}
          </p>
          {overSlideLimit ? (
            <p className="text-xs text-amber-700 mt-1">
              Слишком много слайдов — оставьте не больше {MAX_PRESENTATION_SLIDES}, иначе сохранение и сборка
              не пройдут.
            </p>
          ) : null}
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <div className="inline-flex rounded-lg border border-slate-200 bg-white p-0.5 text-xs font-medium">
            <button
              type="button"
              onClick={() => setMode("preview")}
              disabled={disabled}
              className={`rounded-md px-3 py-1.5 transition-colors ${
                mode === "preview"
                  ? "bg-[var(--primary)] text-white shadow-sm"
                  : "text-slate-600 hover:bg-slate-50"
              }`}
            >
              Просмотр
            </button>
            <button
              type="button"
              onClick={() => setMode("edit")}
              disabled={disabled}
              className={`rounded-md px-3 py-1.5 transition-colors ${
                mode === "edit"
                  ? "bg-[var(--primary)] text-white shadow-sm"
                  : "text-slate-600 hover:bg-slate-50"
              }`}
            >
              Редактирование
            </button>
          </div>

          <button
            type="button"
            onClick={onSave}
            disabled={disabled || !isDirty || isSaving}
            className="rounded-lg border border-sky-200 bg-white px-3 py-1.5 text-xs font-semibold text-[var(--primary)] hover:bg-sky-50 disabled:opacity-50 transition-colors"
          >
            {isSaving ? "Сохранение…" : "Сохранить план"}
          </button>
        </div>
      </div>

      {mode === "preview" ? (
        <div className="p-4 space-y-3 max-h-[min(520px,60vh)] overflow-y-auto bg-slate-50/60">
          {slides.map((slide, index) => (
            <article
              key={`${index}-${slide.title}`}
              className="group relative rounded-xl border border-slate-200/80 bg-white p-4 shadow-sm hover:shadow-md hover:border-sky-200/60 transition-all"
            >
              <div className="absolute -left-px top-4 bottom-4 w-1 rounded-full bg-gradient-to-b from-[var(--primary)] to-sky-400 opacity-80" />
              <div className="flex items-start gap-3 pl-2">
                <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-sky-100 text-sm font-bold text-[var(--primary)]">
                  {index + 1}
                </span>
                <div className="min-w-0 flex-1">
                  <h4 className="text-sm font-semibold text-slate-900 leading-snug">{slide.title}</h4>
                  {slide.bullets.length > 0 ? (
                    <ul className="mt-2.5 space-y-1.5">
                      {slide.bullets.map((bullet, bulletIndex) => (
                        <li
                          key={bulletIndex}
                          className="flex gap-2 text-sm text-slate-600 leading-relaxed"
                        >
                          <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-sky-400" />
                          <span>{bullet}</span>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="mt-2 text-sm text-slate-400 italic">Без пунктов</p>
                  )}
                </div>
              </div>
            </article>
          ))}
        </div>
      ) : (
        <div className="p-4 bg-white">
          <p className="text-xs text-slate-500 mb-2">
            Формат: заголовок слайда — строка с <code className="rounded bg-slate-100 px-1">##</code>,
            пункты — строки с <code className="rounded bg-slate-100 px-1">-</code>. Не более{" "}
            {MAX_PRESENTATION_SLIDES} заголовков ##.
          </p>
          <textarea
            value={outline}
            onChange={(event) => onOutlineChange(event.target.value)}
            disabled={disabled}
            rows={16}
            spellCheck={true}
            className="w-full rounded-xl border border-slate-200 bg-slate-50/50 px-4 py-3 text-sm text-slate-800 leading-relaxed font-mono outline-none focus:border-sky-300 focus:ring-2 focus:ring-sky-100 resize-y min-h-[280px] disabled:opacity-60"
          />
        </div>
      )}
    </div>
  );
}

function slidesLabel(count: number): string {
  const mod10 = count % 10;
  const mod100 = count % 100;
  if (mod10 === 1 && mod100 !== 11) {
    return "слайд";
  }
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) {
    return "слайда";
  }
  return "слайдов";
}
