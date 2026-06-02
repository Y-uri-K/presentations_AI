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
    <div className="overflow-hidden rounded-2xl border border-[var(--border)] bg-[var(--surface)] shadow-sm">
      <div className="flex flex-col gap-3 border-b border-[var(--border)] bg-gradient-to-r from-[var(--surface-muted)] to-[var(--accent-light)] px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h3 className="text-base font-semibold text-[var(--foreground)]">План презентации</h3>
          <p className="mt-0.5 text-xs text-[var(--muted)]">
            {slides.length} {slidesLabel(slides.length)} (макс. {MAX_PRESENTATION_SLIDES})
            {isDirty ? " · есть несохранённые изменения" : null}
          </p>
          {overSlideLimit ? (
            <p className="mt-1 text-xs text-amber-700">
              Слишком много слайдов — оставьте не больше {MAX_PRESENTATION_SLIDES}, иначе сохранение и сборка
              не пройдут.
            </p>
          ) : null}
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <div className="inline-flex rounded-lg border border-[var(--border)] bg-[var(--surface)] p-0.5 text-xs font-medium">
            <button
              type="button"
              onClick={() => setMode("preview")}
              disabled={disabled}
              className={`rounded-md px-3 py-1.5 transition-colors ${
                mode === "preview"
                  ? "bg-[var(--primary)] text-[var(--on-primary)] shadow-sm"
                  : "text-[var(--muted)] hover:bg-[var(--surface-muted)]"
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
                  ? "bg-[var(--primary)] text-[var(--on-primary)] shadow-sm"
                  : "text-[var(--muted)] hover:bg-[var(--surface-muted)]"
              }`}
            >
              Редактирование
            </button>
          </div>

          <button
            type="button"
            onClick={onSave}
            disabled={disabled || !isDirty || isSaving}
            className="rounded-lg border border-[var(--border)] bg-[var(--surface)] px-3 py-1.5 text-xs font-semibold text-[var(--primary)] transition-colors hover:border-[var(--primary)] hover:bg-[var(--surface-muted)] disabled:opacity-50"
          >
            {isSaving ? "Сохранение…" : "Сохранить план"}
          </button>
        </div>
      </div>

      {mode === "preview" ? (
        <div className="max-h-[min(520px,60vh)] space-y-3 overflow-y-auto bg-[var(--surface-muted)] p-4">
          {slides.map((slide, index) => (
            <article
              key={`${index}-${slide.title}`}
              className="group relative rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4 shadow-sm transition-all hover:border-[var(--primary)] hover:shadow-md"
            >
              <div className="absolute bottom-4 top-4 -left-px w-1 rounded-full bg-gradient-to-b from-[var(--primary)] to-[var(--accent)] opacity-80" />
              <div className="flex items-start gap-3 pl-2">
                <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-[var(--accent-light)] text-sm font-bold text-[var(--primary)]">
                  {index + 1}
                </span>
                <div className="min-w-0 flex-1">
                  <h4 className="text-sm font-semibold leading-snug text-[var(--foreground)]">{slide.title}</h4>
                  {slide.bullets.length > 0 ? (
                    <ul className="mt-2.5 space-y-1.5">
                      {slide.bullets.map((bullet, bulletIndex) => (
                        <li
                          key={bulletIndex}
                          className="flex gap-2 text-sm leading-relaxed text-[var(--muted)]"
                        >
                          <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-[var(--accent)]" />
                          <span>{bullet}</span>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="mt-2 text-sm italic text-[var(--subtle)]">Без пунктов</p>
                  )}
                </div>
              </div>
            </article>
          ))}
        </div>
      ) : (
        <div className="bg-[var(--surface)] p-4">
          <p className="mb-2 text-xs text-[var(--muted)]">
            Формат: заголовок слайда — строка с <code className="rounded bg-[var(--surface-muted)] px-1">##</code>,
            пункты — строки с <code className="rounded bg-[var(--surface-muted)] px-1">-</code>. Не более{" "}
            {MAX_PRESENTATION_SLIDES} заголовков ##.
          </p>
          <textarea
            value={outline}
            onChange={(event) => onOutlineChange(event.target.value)}
            disabled={disabled}
            rows={16}
            spellCheck={true}
            className="min-h-[280px] w-full resize-y rounded-xl border border-[var(--border)] bg-[var(--background)] px-4 py-3 font-mono text-sm leading-relaxed text-[var(--foreground)] outline-none focus:border-[var(--primary)] focus:ring-2 focus:ring-[color:var(--focus-ring)] disabled:opacity-60"
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
