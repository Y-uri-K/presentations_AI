"use client";

import Image from "next/image";
import { useEffect, useMemo, useRef, useState } from "react";

import { ApiError } from "@/lib/api/auth";
import {
  downloadPublicTemplate,
  fetchPublicTemplates,
  fetchTemplatePreview,
  formatFileSize,
  ratePublicTemplate,
  type PublicTemplateListItem,
  type PublicTemplateSort,
  type TemplatePreview,
  uploadPublicTemplate,
} from "@/lib/api/templates";
import { ErrorMessage } from "@/components/ui/ErrorMessage";

const ACCEPT = ".pptx,.pdf,application/pdf,application/vnd.openxmlformats-officedocument.presentationml.presentation";

const SORT_OPTIONS: Array<{ value: PublicTemplateSort; label: string }> = [
  { value: "new", label: "Сначала новые" },
  { value: "name", label: "По названию" },
  { value: "downloads", label: "По скачиваниям" },
  { value: "rating", label: "По оценке" },
];

function formatRating(value: number): string {
  return value > 0 ? value.toFixed(1) : "—";
}

function formatRatingCount(count: number): string {
  const absCount = Math.abs(count);
  const lastTwoDigits = absCount % 100;
  const lastDigit = absCount % 10;

  if (lastTwoDigits >= 11 && lastTwoDigits <= 14) {
    return `${count} оценок`;
  }
  if (lastDigit === 1) {
    return `${count} оценка`;
  }
  if (lastDigit >= 2 && lastDigit <= 4) {
    return `${count} оценки`;
  }
  return `${count} оценок`;
}

export function PublicTemplatesClient() {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [templates, setTemplates] = useState<PublicTemplateListItem[]>([]);
  const [search, setSearch] = useState("");
  const [sort, setSort] = useState<PublicTemplateSort>("new");
  const [isLoading, setIsLoading] = useState(true);
  const [isUploading, setIsUploading] = useState(false);
  const [activeDownloadId, setActiveDownloadId] = useState<number | null>(null);
  const [activeRatingId, setActiveRatingId] = useState<number | null>(null);
  const [preview, setPreview] = useState<TemplatePreview | null>(null);
  const [previewLoadingId, setPreviewLoadingId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  const normalizedSearch = useMemo(() => search.trim(), [search]);

  useEffect(() => {
    let cancelled = false;

    async function loadTemplates() {
      setIsLoading(true);
      setError(null);
      try {
        const items = await fetchPublicTemplates({ search: normalizedSearch, sort });
        if (!cancelled) {
          setTemplates(items);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof ApiError ? err.message : "Не удалось загрузить шаблоны");
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    const timer = window.setTimeout(() => {
      void loadTemplates();
    }, 250);

    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [normalizedSearch, sort]);

  async function handleFileChange(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) {
      return;
    }

    const lowerName = file.name.toLowerCase();
    if (!lowerName.endsWith(".pptx") && !lowerName.endsWith(".pdf")) {
      setError("Допустимы только файлы .pptx и .pdf");
      return;
    }

    setIsUploading(true);
    setError(null);
    try {
      const created = await uploadPublicTemplate(file);
      setTemplates((prev) => [created, ...prev]);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Не удалось загрузить шаблон");
    } finally {
      setIsUploading(false);
    }
  }

  async function handleDownload(template: PublicTemplateListItem) {
    setActiveDownloadId(template.id);
    setError(null);
    try {
      await downloadPublicTemplate(template);
      setTemplates((prev) =>
        prev.map((item) =>
          item.id === template.id
            ? { ...item, download_count: item.download_count + 1 }
            : item,
        ),
      );
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Не удалось скачать шаблон");
    } finally {
      setActiveDownloadId(null);
    }
  }

  async function handleRate(templateId: number, rating: number) {
    setActiveRatingId(templateId);
    setError(null);
    try {
      const result = await ratePublicTemplate(templateId, rating);
      setTemplates((prev) =>
        prev.map((item) =>
          item.id === templateId
            ? {
                ...item,
                rating_avg: result.rating_avg,
                rating_count: result.rating_count,
                user_rating: result.user_rating,
              }
            : item,
        ),
      );
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Не удалось сохранить оценку");
    } finally {
      setActiveRatingId(null);
    }
  }

  async function handlePreview(templateId: number) {
    setPreviewLoadingId(templateId);
    setError(null);
    try {
      setPreview(await fetchTemplatePreview(templateId));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Не удалось открыть предпросмотр");
    } finally {
      setPreviewLoadingId(null);
    }
  }

  return (
    <section className="space-y-5">
      <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-5">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
          <div className="grid flex-1 gap-3 sm:grid-cols-[1fr_220px]">
            <label className="block">
              <span className="text-sm font-medium text-[var(--foreground)]">Название</span>
              <input
                type="search"
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Найти шаблон"
                className="mt-1 w-full rounded-lg border border-[var(--border)] bg-[var(--background)] px-3 py-2 text-sm text-[var(--foreground)] outline-none transition-colors focus:border-[var(--primary)] focus:ring-2 focus:ring-[color:var(--focus-ring)]"
              />
            </label>
            <label className="block">
              <span className="text-sm font-medium text-[var(--foreground)]">Сортировка</span>
              <select
                value={sort}
                onChange={(event) => setSort(event.target.value as PublicTemplateSort)}
                className="mt-1 w-full rounded-lg border border-[var(--border)] bg-[var(--background)] px-3 py-2 text-sm text-[var(--foreground)] outline-none transition-colors focus:border-[var(--primary)] focus:ring-2 focus:ring-[color:var(--focus-ring)]"
              >
                {SORT_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            disabled={isUploading}
            className="rounded-lg bg-[var(--primary)] px-4 py-2 text-sm font-semibold text-[var(--on-primary)] transition-colors hover:bg-[var(--primary-dark)] disabled:opacity-60"
          >
            {isUploading ? "Загрузка…" : "Выложить шаблон"}
          </button>
          <input
            ref={fileInputRef}
            type="file"
            accept={ACCEPT}
            className="hidden"
            onChange={handleFileChange}
          />
        </div>
        {error ? <ErrorMessage className="mt-4">{error}</ErrorMessage> : null}
      </div>

      {isLoading ? (
        <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-6 text-sm text-[var(--muted)]">
          Загрузка шаблонов…
        </div>
      ) : templates.length === 0 ? (
        <div className="rounded-xl border border-dashed border-[var(--border)] bg-[var(--surface)] p-8 text-center">
          <h2 className="font-semibold text-[var(--foreground)]">Шаблонов пока нет</h2>
          <p className="mt-2 text-sm text-[var(--muted)]">
            Выложите первый публичный шаблон, чтобы другие пользователи могли его оценить и скачать.
          </p>
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {templates.map((template) => (
            <article
              key={template.id}
              className="flex min-h-[260px] flex-col rounded-xl border border-[var(--border)] bg-[var(--surface)] p-5 shadow-sm"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="truncate text-lg font-semibold text-[var(--foreground)]">
                    {template.name}
                  </p>
                  <p className="mt-1 text-sm text-[var(--muted)]">
                    Автор: {template.author_username}
                  </p>
                </div>
                <span className="shrink-0 rounded-md border border-[var(--border)] bg-[var(--surface-muted)] px-2 py-1 text-xs font-bold uppercase text-[var(--muted)]">
                  {template.file_type}
                </span>
              </div>

              <dl className="mt-4 grid grid-cols-2 gap-3 text-sm">
                <div>
                  <dt className="text-[var(--subtle)]">Размер</dt>
                  <dd className="font-medium text-[var(--foreground)]">
                    {formatFileSize(template.size_bytes)}
                  </dd>
                </div>
                <div>
                  <dt className="text-[var(--subtle)]">Скачивания</dt>
                  <dd className="font-medium text-[var(--foreground)]">
                    {template.download_count}
                  </dd>
                </div>
                <div>
                  <dt className="text-[var(--subtle)]">Оценка</dt>
                  <dd className="font-medium text-[var(--foreground)]">
                    {formatRating(template.rating_avg)}
                  </dd>
                </div>
                <div>
                  <dt className="text-[var(--subtle)]">Всего оценок</dt>
                  <dd className="font-medium text-[var(--foreground)]">
                    {formatRatingCount(template.rating_count)}
                  </dd>
                </div>
                <div>
                  <dt className="text-[var(--subtle)]">Файл</dt>
                  <dd className="truncate font-medium text-[var(--foreground)]">
                    {template.original_filename}
                  </dd>
                </div>
              </dl>

              <div className="mt-4">
                <p className="text-xs font-medium uppercase tracking-wide text-[var(--subtle)]">
                  Ваша оценка
                </p>
                <div className="mt-2 flex gap-1">
                  {[1, 2, 3, 4, 5].map((rating) => {
                    const isActive = (template.user_rating ?? 0) >= rating;
                    return (
                      <button
                        key={rating}
                        type="button"
                        onClick={() => handleRate(template.id, rating)}
                        disabled={activeRatingId === template.id}
                        className={`h-8 w-8 rounded-md border text-sm font-semibold transition-colors disabled:opacity-60 ${
                          isActive
                            ? "border-[var(--primary)] bg-[var(--accent-light)] text-[var(--foreground)]"
                            : "border-[var(--border)] bg-[var(--surface-muted)] text-[var(--muted)] hover:border-[var(--primary)]"
                        }`}
                        aria-label={`Поставить ${rating}`}
                      >
                        {rating}
                      </button>
                    );
                  })}
                </div>
              </div>

              <div className="mt-auto flex gap-2 pt-5">
                <button
                  type="button"
                  onClick={() => handlePreview(template.id)}
                  disabled={previewLoadingId === template.id}
                  className="flex-1 rounded-lg border border-[var(--border)] px-3 py-2 text-sm font-semibold text-[var(--foreground)] transition-colors hover:border-[var(--primary)] hover:bg-[var(--surface-muted)] disabled:opacity-60"
                >
                  {previewLoadingId === template.id ? "Открытие…" : "Предпросмотр"}
                </button>
                <button
                  type="button"
                  onClick={() => handleDownload(template)}
                  disabled={activeDownloadId === template.id}
                  className="flex-1 rounded-lg bg-[var(--primary)] px-3 py-2 text-sm font-semibold text-[var(--on-primary)] transition-colors hover:bg-[var(--primary-dark)] disabled:opacity-60"
                >
                  {activeDownloadId === template.id ? "Скачивание…" : "Скачать"}
                </button>
              </div>
            </article>
          ))}
        </div>
      )}

      {preview ? (
        <div
          className="fixed inset-0 z-30 flex items-center justify-center bg-slate-950/60 px-4 py-8"
          role="dialog"
          aria-modal="true"
        >
          <div className="max-h-full w-full max-w-3xl overflow-y-auto rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-6 shadow-xl">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-sm font-medium uppercase tracking-wide text-[var(--subtle)]">
                  Предпросмотр
                </p>
                <h2 className="mt-1 text-xl font-semibold text-[var(--foreground)]">
                  {preview.name}
                </h2>
              </div>
              <button
                type="button"
                onClick={() => setPreview(null)}
                className="rounded-lg border border-[var(--border)] px-3 py-1.5 text-sm font-medium text-[var(--foreground)] hover:bg-[var(--surface-muted)]"
              >
                Закрыть
              </button>
            </div>

            <div className="mt-5 overflow-hidden rounded-xl border border-[var(--border)] bg-[var(--surface-muted)]">
              {preview.office_viewer_url ? (
                <iframe
                  title={`Предпросмотр шаблона ${preview.name}`}
                  src={preview.office_viewer_url}
                  className="h-[560px] w-full bg-white"
                  allowFullScreen
                />
              ) : preview.image_data_url ? (
                <Image
                  src={preview.image_data_url}
                  alt={`Предпросмотр шаблона ${preview.name}`}
                  width={1200}
                  height={800}
                  unoptimized
                  className="mx-auto max-h-[560px] w-full object-contain"
                />
              ) : (
                <div className="p-8 text-center">
                  <p className="text-lg font-semibold text-[var(--foreground)]">
                    Визуальный предпросмотр недоступен
                  </p>
                  <p className="mx-auto mt-2 max-w-md text-sm text-[var(--muted)]">
                    Чтобы увидеть оформление полностью, скачайте файл.
                  </p>
                </div>
              )}
            </div>

            {preview.preview_kind === "office" ? (
              <p className="mt-3 rounded-lg border border-[var(--border)] bg-[var(--surface-muted)] px-3 py-2 text-xs text-[var(--muted)]">
                Предпросмотр PPTX открывается через Microsoft Office Web Viewer. Он работает,
                только если URL backend доступен Microsoft извне.
              </p>
            ) : null}

            <dl className="mt-5 grid gap-3 text-sm sm:grid-cols-3">
              <div className="rounded-lg bg-[var(--surface-muted)] p-3">
                <dt className="text-[var(--subtle)]">Тип</dt>
                <dd className="font-semibold uppercase text-[var(--foreground)]">
                  {preview.file_type}
                </dd>
              </div>
              <div className="rounded-lg bg-[var(--surface-muted)] p-3">
                <dt className="text-[var(--subtle)]">Размер</dt>
                <dd className="font-semibold text-[var(--foreground)]">
                  {formatFileSize(preview.size_bytes)}
                </dd>
              </div>
              <div className="rounded-lg bg-[var(--surface-muted)] p-3">
                <dt className="text-[var(--subtle)]">Скачивания</dt>
                <dd className="font-semibold text-[var(--foreground)]">
                  {preview.download_count}
                </dd>
              </div>
            </dl>
          </div>
        </div>
      ) : null}
    </section>
  );
}
