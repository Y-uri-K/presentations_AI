"use client";

import { useEffect, useState } from "react";

import { ApiError } from "@/lib/api/auth";
import {
  deletePresentation,
  downloadPresentation,
  fetchPresentations,
  renamePresentation,
  type PresentationListItem,
} from "@/lib/api/presentations";
import { isPresentationNotFoundError } from "@/lib/api/errors";
import { ErrorMessage } from "@/components/ui/ErrorMessage";

type SavedPresentationsPanelProps = {
  refreshSignal: number;
};

function statusLabel(status: PresentationListItem["status"]) {
  const labels: Record<PresentationListItem["status"], string> = {
    draft: "план",
    building: "сборка",
    ready: "готово",
    failed: "ошибка",
  };
  return labels[status];
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat("ru-RU", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

export function SavedPresentationsPanel({ refreshSignal }: SavedPresentationsPanelProps) {
  const [presentations, setPresentations] = useState<PresentationListItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editingTitle, setEditingTitle] = useState("");
  const [renamingId, setRenamingId] = useState<number | null>(null);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [downloadingId, setDownloadingId] = useState<number | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadPresentations() {
      setIsLoading(true);
      try {
        const items = await fetchPresentations();
        if (!cancelled) {
          setPresentations(items);
          setError(null);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof ApiError ? err.message : "Не удалось загрузить презентации");
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    void loadPresentations();

    return () => {
      cancelled = true;
    };
  }, [refreshSignal]);

  function startEditing(item: PresentationListItem) {
    setEditingId(item.id);
    setEditingTitle(item.title);
    setError(null);
  }

  function cancelEditing() {
    setEditingId(null);
    setEditingTitle("");
  }

  async function saveRename(presentationId: number) {
    const trimmed = editingTitle.trim();
    if (!trimmed) {
      setError("Название не может быть пустым");
      return;
    }

    setRenamingId(presentationId);
    setError(null);
    try {
      const updated = await renamePresentation(presentationId, trimmed);
      setPresentations((prev) =>
        prev.map((item) => (item.id === presentationId ? updated : item)),
      );
      cancelEditing();
    } catch (err) {
      if (isPresentationNotFoundError(err)) {
        setPresentations((prev) => prev.filter((item) => item.id !== presentationId));
        cancelEditing();
      } else {
        setError(err instanceof ApiError ? err.message : "Не удалось переименовать презентацию");
      }
    } finally {
      setRenamingId(null);
    }
  }

  async function handleDownload(item: PresentationListItem) {
    if (!item.has_download || item.status !== "ready") {
      setError("Файл презентации ещё не готов");
      return;
    }
    setDownloadingId(item.id);
    setError(null);
    try {
      await downloadPresentation(item.id, item.title);
    } catch (err) {
      if (isPresentationNotFoundError(err)) {
        setPresentations((prev) => prev.filter((presentation) => presentation.id !== item.id));
      } else {
        setError(err instanceof ApiError ? err.message : "Не удалось скачать презентацию");
      }
    } finally {
      setDownloadingId(null);
    }
  }

  async function handleDelete(item: PresentationListItem) {
    const confirmed = window.confirm(`Удалить презентацию «${item.title}»?`);
    if (!confirmed) {
      return;
    }

    setDeletingId(item.id);
    setError(null);
    try {
      await deletePresentation(item.id);
      setPresentations((prev) => prev.filter((presentation) => presentation.id !== item.id));
    } catch (err) {
      if (isPresentationNotFoundError(err)) {
        setPresentations((prev) => prev.filter((presentation) => presentation.id !== item.id));
      } else {
        setError(err instanceof ApiError ? err.message : "Не удалось удалить презентацию");
      }
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <div className="flex min-h-[280px] flex-col rounded-xl border border-[var(--border)] bg-[var(--surface)] p-6">
      <div>
        <h2 className="font-semibold text-[var(--foreground)]">Мои презентации</h2>
        <p className="mt-1 text-sm text-[var(--muted)]">
          Сохранённые планы и готовые PPTX
        </p>
      </div>

      {error ? (
        <ErrorMessage className="mt-3">{error}</ErrorMessage>
      ) : null}

      <div className="mt-4 flex-1">
        {isLoading ? (
          <p className="text-sm text-[var(--subtle)]">Загрузка списка…</p>
        ) : presentations.length === 0 ? (
          <p className="text-sm text-[var(--subtle)]">
            Пока нет сохранённых презентаций. Сгенерируйте план и соберите PPTX.
          </p>
        ) : (
          <ul className="max-h-64 space-y-2 overflow-y-auto pr-1">
            {presentations.map((item) => (
              <li
                key={item.id}
                className="rounded-lg border border-[var(--border)] bg-[var(--surface-muted)] px-3 py-2"
              >
                <div className="flex items-start gap-2">
                  <span className="shrink-0 rounded-md border border-[var(--border)] bg-[var(--surface)] px-1.5 py-0.5 text-[10px] font-bold uppercase text-[var(--muted)]">
                    {statusLabel(item.status)}
                  </span>
                  <div className="min-w-0 flex-1">
                    {editingId === item.id ? (
                      <div className="flex items-center gap-1">
                        <input
                          type="text"
                          value={editingTitle}
                          maxLength={255}
                          disabled={renamingId === item.id}
                          onChange={(event) => setEditingTitle(event.target.value)}
                          onKeyDown={(event) => {
                            if (event.key === "Enter") {
                              event.preventDefault();
                              void saveRename(item.id);
                            }
                            if (event.key === "Escape") {
                              cancelEditing();
                            }
                          }}
                          className="w-full min-w-0 rounded-md border border-[var(--border)] bg-[var(--background)] px-2 py-1 text-sm text-[var(--foreground)] outline-none focus:border-[var(--primary)] focus:ring-1 focus:ring-[color:var(--focus-ring)]"
                        />
                        <button
                          type="button"
                          onClick={() => saveRename(item.id)}
                          disabled={renamingId === item.id}
                          className="shrink-0 text-xs font-medium text-[var(--success-text)] hover:opacity-80 disabled:opacity-50"
                        >
                          {renamingId === item.id ? "…" : "OK"}
                        </button>
                        <button
                          type="button"
                          onClick={cancelEditing}
                          disabled={renamingId === item.id}
                          className="shrink-0 text-xs font-medium text-[var(--muted)] hover:text-[var(--foreground)] disabled:opacity-50"
                        >
                          x
                        </button>
                      </div>
                    ) : (
                      <p className="truncate text-sm font-medium text-[var(--foreground)]">
                        {item.title}
                      </p>
                    )}
                    <p className="mt-0.5 truncate text-xs text-[var(--subtle)]">
                      {formatDate(item.updated_at)}
                      {item.slide_count ? ` · ${item.slide_count} слайд(ов)` : ""}
                      {item.template_name ? ` · ${item.template_name}` : ""}
                    </p>
                  </div>
                </div>

                <div className="mt-2 flex flex-wrap justify-end gap-3">
                  {editingId !== item.id ? (
                    <button
                      type="button"
                      onClick={() => startEditing(item)}
                      className="text-xs font-medium text-[var(--muted)] hover:text-[var(--foreground)]"
                    >
                      Имя
                    </button>
                  ) : null}
                  <button
                    type="button"
                    onClick={() => handleDownload(item)}
                    disabled={!item.has_download || item.status !== "ready" || downloadingId === item.id}
                    className="text-xs font-medium text-[var(--primary)] hover:text-[var(--primary-dark)] disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    {downloadingId === item.id ? "Скачивание…" : "Скачать"}
                  </button>
                  <button
                    type="button"
                    onClick={() => handleDelete(item)}
                    disabled={deletingId === item.id}
                    className="text-xs font-medium text-[var(--danger-text)] hover:opacity-80 disabled:opacity-50"
                  >
                    {deletingId === item.id ? "…" : "Удалить"}
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
