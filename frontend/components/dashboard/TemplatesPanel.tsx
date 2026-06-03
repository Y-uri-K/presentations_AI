"use client";

import { useEffect, useRef, useState } from "react";

import {
  deleteTemplate,
  downloadTemplate,
  fetchTemplates,
  formatFileSize,
  renameTemplate,
  type TemplateListItem,
  uploadTemplate,
} from "@/lib/api/templates";
import { ApiError } from "@/lib/api/auth";
import { useTemplateSelection } from "@/components/dashboard/TemplateSelectionContext";
import { ErrorMessage } from "@/components/ui/ErrorMessage";

const ACCEPT = ".pptx,.pdf,application/pdf,application/vnd.openxmlformats-officedocument.presentationml.presentation";

export function TemplatesPanel() {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { selectedTemplateId, selectTemplate } = useTemplateSelection();
  const [templates, setTemplates] = useState<TemplateListItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isUploading, setIsUploading] = useState(false);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editingName, setEditingName] = useState("");
  const [renamingId, setRenamingId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadInitialTemplates() {
      try {
        const items = await fetchTemplates();
        if (!cancelled) {
          setTemplates(items);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof ApiError ? err.message : "Не удалось загрузить список шаблонов");
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    void loadInitialTemplates();

    return () => {
      cancelled = true;
    };
  }, []);

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
      const created = await uploadTemplate(file);
      setTemplates((prev) => [created, ...prev]);
      selectTemplate(created);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Не удалось загрузить шаблон");
    } finally {
      setIsUploading(false);
    }
  }

  async function handleDelete(templateId: number) {
    setDeletingId(templateId);
    setError(null);
    try {
      await deleteTemplate(templateId);
      setTemplates((prev) => prev.filter((item) => item.id !== templateId));
      if (selectedTemplateId === templateId) {
        selectTemplate(null);
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Не удалось удалить шаблон");
    } finally {
      setDeletingId(null);
    }
  }

  async function handleDownload(template: TemplateListItem) {
    setError(null);
    try {
      await downloadTemplate(template);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Не удалось скачать шаблон");
    }
  }

  function startEditing(template: TemplateListItem) {
    setEditingId(template.id);
    setEditingName(template.name);
    setError(null);
  }

  function cancelEditing() {
    setEditingId(null);
    setEditingName("");
  }

  async function saveRename(templateId: number) {
    const trimmed = editingName.trim();
    if (!trimmed) {
      setError("Название не может быть пустым");
      return;
    }

    setRenamingId(templateId);
    setError(null);
    try {
      const updated = await renameTemplate(templateId, trimmed);
      setTemplates((prev) =>
        prev.map((item) => (item.id === templateId ? updated : item)),
      );
      if (selectedTemplateId === templateId) {
        selectTemplate(updated);
      }
      cancelEditing();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Не удалось переименовать шаблон");
    } finally {
      setRenamingId(null);
    }
  }

  return (
    <div className="flex min-h-[280px] flex-col rounded-xl border border-[var(--border)] bg-[var(--surface)] p-6">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="font-semibold text-[var(--foreground)]">Шаблоны</h2>
          <p className="mt-1 text-sm text-[var(--muted)]">PPTX/PDF — выберите активный шаблон</p>
        </div>
        <button
          type="button"
          onClick={() => fileInputRef.current?.click()}
          disabled={isUploading}
          className="shrink-0 rounded-lg bg-[var(--primary)] px-3 py-1.5 text-sm font-semibold text-[var(--on-primary)] transition-colors hover:bg-[var(--primary-dark)] disabled:opacity-60"
        >
          {isUploading ? "Загрузка…" : "Загрузить"}
        </button>
        <input
          ref={fileInputRef}
          type="file"
          accept={ACCEPT}
          className="hidden"
          onChange={handleFileChange}
        />
      </div>

      {error ? (
        <ErrorMessage className="mt-3">{error}</ErrorMessage>
      ) : null}

      <div className="mt-4 flex-1">
        {isLoading ? (
          <p className="text-sm text-[var(--subtle)]">Загрузка списка…</p>
        ) : templates.length === 0 ? (
          <p className="text-sm text-[var(--subtle)]">
            Пока нет шаблонов. Нажмите «Загрузить», чтобы добавить презентацию.
          </p>
        ) : (
          <ul className="max-h-48 space-y-2 overflow-y-auto pr-1">
            {templates.map((template) => {
              const isSelected = selectedTemplateId === template.id;
              return (
              <li
                key={template.id}
                className={`flex items-center gap-2 rounded-lg border px-3 py-2 ${
                  isSelected
                    ? "border-[var(--primary)] bg-[var(--accent-light)] ring-1 ring-[color:var(--focus-ring)]"
                    : "border-[var(--border)] bg-[var(--surface-muted)]"
                }`}
              >
                <button
                  type="button"
                  onClick={() => selectTemplate(isSelected ? null : template)}
                  title={isSelected ? "Снять выбор" : "Использовать шаблон"}
                  className={`shrink-0 h-4 w-4 rounded-full border-2 flex items-center justify-center ${
                    isSelected
                      ? "border-[var(--primary)] bg-[var(--primary)]"
                      : "border-[var(--border)] bg-[var(--surface)] hover:border-[var(--primary)]"
                  }`}
                >
                  {isSelected ? (
                    <span className="h-1.5 w-1.5 rounded-full bg-[var(--on-primary)]" />
                  ) : null}
                </button>
                <span className="shrink-0 rounded-md border border-[var(--border)] bg-[var(--surface)] px-1.5 py-0.5 text-[10px] font-bold uppercase text-[var(--muted)]">
                  {template.file_type}
                </span>
                <div className="min-w-0 flex-1">
                  {editingId === template.id ? (
                    <div className="flex items-center gap-1">
                      <input
                        type="text"
                        value={editingName}
                        onChange={(event) => setEditingName(event.target.value)}
                        maxLength={255}
                        disabled={renamingId === template.id}
                        className="w-full min-w-0 rounded-md border border-[var(--border)] bg-[var(--background)] px-2 py-1 text-sm text-[var(--foreground)] outline-none focus:border-[var(--primary)] focus:ring-1 focus:ring-[color:var(--focus-ring)]"
                        onKeyDown={(event) => {
                          if (event.key === "Enter") {
                            event.preventDefault();
                            void saveRename(template.id);
                          }
                          if (event.key === "Escape") {
                            cancelEditing();
                          }
                        }}
                      />
                      <button
                        type="button"
                        onClick={() => saveRename(template.id)}
                        disabled={renamingId === template.id}
                        className="shrink-0 text-xs font-medium text-[var(--success-text)] hover:opacity-80 disabled:opacity-50"
                      >
                        {renamingId === template.id ? "…" : "OK"}
                      </button>
                      <button
                        type="button"
                        onClick={cancelEditing}
                        disabled={renamingId === template.id}
                        className="shrink-0 text-xs font-medium text-[var(--muted)] hover:text-[var(--foreground)] disabled:opacity-50"
                      >
                        ✕
                      </button>
                    </div>
                  ) : (
                    <p className="truncate text-sm font-medium text-[var(--foreground)]">{template.name}</p>
                  )}
                  <p className="truncate text-xs text-[var(--subtle)]">
                    {formatFileSize(template.size_bytes)}
                  </p>
                </div>
                {editingId !== template.id ? (
                  <button
                    type="button"
                    onClick={() => startEditing(template)}
                    className="shrink-0 text-xs font-medium text-[var(--muted)] hover:text-[var(--foreground)]"
                  >
                    Имя
                  </button>
                ) : null}
                <button
                  type="button"
                  onClick={() => handleDownload(template)}
                  className="shrink-0 text-xs font-medium text-[var(--primary)] hover:text-[var(--primary-dark)]"
                >
                  Скачать
                </button>
                <button
                  type="button"
                  onClick={() => handleDelete(template.id)}
                  disabled={deletingId === template.id}
                  className="shrink-0 text-xs font-medium text-[var(--danger-text)] hover:opacity-80 disabled:opacity-50"
                >
                  {deletingId === template.id ? "…" : "Удалить"}
                </button>
              </li>
            );
            })}
          </ul>
        )}
      </div>
    </div>
  );
}
