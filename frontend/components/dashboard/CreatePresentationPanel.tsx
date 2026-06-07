"use client";

import { useEffect, useMemo, useRef, useState } from "react";

import {
  type AgentId,
  type AgentInfo,
  fetchAgents,
} from "@/lib/api/agents";
import { ApiError } from "@/lib/api/auth";
import {
  buildPresentation,
  createPresentation,
  downloadPresentation,
  fetchPresentations,
  getPresentationStatus,
  updatePresentationOutline,
  type PresentationStatus,
  type PresentationStatusResponse,
} from "@/lib/api/presentations";
import { pickPreferredAgent } from "@/lib/agents/pickPreferredAgent";
import { PresentationPlanEditor } from "@/components/dashboard/PresentationPlanEditor";
import { useTemplateSelection } from "@/components/dashboard/TemplateSelectionContext";
import { ErrorMessage } from "@/components/ui/ErrorMessage";
import { isPresentationNotFoundError } from "@/lib/api/errors";
import { outlineTitleFromMarkdown, parseOutline } from "@/lib/outline/parseOutline";
import { MAX_PRESENTATION_SLIDES } from "@/lib/presentation/limits";

function buildStageLabel(stage: string | null): string {
  const labels: Record<string, string> = {
    queued: "в очереди",
    started: "старт",
    template_analysis: "анализ шаблона",
    blueprint: "макеты слайдов",
    images: "картинки",
    pptx_fill: "заполнение PPTX",
    content_plan: "план контента",
    done: "готово",
    failed: "ошибка",
  };
  if (!stage) {
    return "обработка";
  }
  return labels[stage] ?? "обработка";
}

const AGENT_LABELS: Record<AgentId, string> = {
  mimo: "MiMo (основной)",
  ollama: "Ollama",
  polza: "Polza (Gemini)",
};

const SOURCE_ACCEPT =
  ".docx,.pdf,.md,.markdown,.txt,application/pdf,text/plain,text/markdown,application/vnd.openxmlformats-officedocument.wordprocessingml.document";

const MAX_SOURCE_FILES = 5;
const ACTIVE_PRESENTATION_ID_KEY = "aideck_active_presentation_id";
const WORKSPACE_RESET_KEY = "aideck_workspace_reset";

function isAllowedSourceFile(file: File): boolean {
  const name = file.name.toLowerCase();
  return (
    name.endsWith(".docx") ||
    name.endsWith(".pdf") ||
    name.endsWith(".md") ||
    name.endsWith(".markdown") ||
    name.endsWith(".txt")
  );
}

type CreatePresentationPanelProps = {
  onPresentationsChanged?: () => void;
};

function saveActivePresentationId(id: number) {
  localStorage.setItem(ACTIVE_PRESENTATION_ID_KEY, String(id));
}

function readActivePresentationId(): number | null {
  const raw = localStorage.getItem(ACTIVE_PRESENTATION_ID_KEY);
  const parsed = raw ? Number.parseInt(raw, 10) : Number.NaN;
  return Number.isFinite(parsed) && parsed > 0 ? parsed : null;
}

function clearActivePresentationId() {
  localStorage.removeItem(ACTIVE_PRESENTATION_ID_KEY);
}

function markWorkspaceReset() {
  localStorage.setItem(WORKSPACE_RESET_KEY, "1");
}

function clearWorkspaceReset() {
  localStorage.removeItem(WORKSPACE_RESET_KEY);
}

function wasWorkspaceReset() {
  return localStorage.getItem(WORKSPACE_RESET_KEY) === "1";
}

export function CreatePresentationPanel({ onPresentationsChanged }: CreatePresentationPanelProps) {
  const sourceInputRef = useRef<HTMLInputElement>(null);
  const { selectedTemplate, selectedTemplateId } = useTemplateSelection();

  const [agents, setAgents] = useState<AgentInfo[]>([]);
  const [agentId, setAgentId] = useState<AgentId>("mimo");
  const [prompt, setPrompt] = useState("");
  const [sourceFiles, setSourceFiles] = useState<File[]>([]);
  const [outline, setOutline] = useState<string | null>(null);
  const [savedOutline, setSavedOutline] = useState<string | null>(null);
  const [presentationId, setPresentationId] = useState<number | null>(null);
  const [presentationTitle, setPresentationTitle] = useState("Презентация");
  const [buildStatus, setBuildStatus] = useState<PresentationStatus | null>(null);
  const [buildTemplateFileType, setBuildTemplateFileType] = useState<"pptx" | "pdf" | null>(
    null,
  );
  const [slideCount, setSlideCount] = useState<number | null>(null);
  const [isLoadingAgents, setIsLoadingAgents] = useState(true);
  const [isCreating, setIsCreating] = useState(false);
  const [isSavingOutline, setIsSavingOutline] = useState(false);
  const [isBuilding, setIsBuilding] = useState(false);
  const [buildStage, setBuildStage] = useState<string | null>(null);
  const [isDownloading, setIsDownloading] = useState(false);
  const [generateImages, setGenerateImages] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const effectiveTemplateType =
    buildTemplateFileType ?? selectedTemplate?.file_type ?? null;

  const isOutlineDirty =
    outline !== null && savedOutline !== null && outline.trim() !== savedOutline.trim();

  const planSlideCount = useMemo(
    () => (savedOutline ? parseOutline(savedOutline).length : 0),
    [savedOutline],
  );
  const planOverLimit = planSlideCount > MAX_PRESENTATION_SLIDES;

  const canBuild =
    presentationId != null &&
    presentationId > 0 &&
    (effectiveTemplateType === null || effectiveTemplateType === "pptx" || effectiveTemplateType === "pdf") &&
    buildStatus !== "ready" &&
    !isOutlineDirty &&
    !planOverLimit;

  const buildDisabledReason =
    presentationId === null
      ? null
      : planOverLimit
        ? `В плане ${planSlideCount} слайдов — максимум ${MAX_PRESENTATION_SLIDES}`
        : isOutlineDirty
        ? "Сохраните план перед сборкой презентации"
        : effectiveTemplateType !== null && effectiveTemplateType !== "pptx" && effectiveTemplateType !== "pdf"
            ? "Для сборки нужен шаблон PPTX или PDF"
            : buildStatus === "ready"
              ? null
              : null;

  useEffect(() => {
    fetchAgents()
      .then((list) => {
        setAgents(list);
        const preferred = pickPreferredAgent(list);
        if (preferred) {
          setAgentId(preferred);
        }
      })
      .catch((err) => {
        setError(err instanceof ApiError ? err.message : "Не удалось загрузить агентов");
      })
      .finally(() => setIsLoadingAgents(false));
  }, []);

  useEffect(() => {
    let cancelled = false;

    function applyStatus(status: PresentationStatusResponse) {
      setPresentationId(status.id);
      setPresentationTitle(status.title);
      setOutline(status.outline ?? null);
      setSavedOutline(status.outline ?? null);
      setBuildStatus(status.status);
      setBuildStage(status.build_stage);
      setBuildTemplateFileType(status.template_file_type);
      setSlideCount(status.slide_count);
      setPrompt("");
      setSourceFiles([]);
    }

    async function resumeActivePresentation() {
      let activeId = readActivePresentationId();
      if (!activeId && wasWorkspaceReset()) {
        return;
      }
      if (!activeId) {
        const latest = (await fetchPresentations()).find((item) =>
          item.status === "ready" && item.has_download,
        );
        activeId = latest?.id ?? null;
        if (activeId) {
          saveActivePresentationId(activeId);
        }
      }
      if (!activeId) {
        return;
      }

      try {
        const status = await getPresentationStatus(activeId);
        if (cancelled) {
          return;
        }
        applyStatus(status);
        if (status.status === "building") {
          setIsBuilding(true);
          setNotice("Сборка была восстановлена после перезагрузки страницы");
          const result = await buildPresentation(activeId, {
            generateImages: true,
            onPoll: (nextStatus) => {
              if (cancelled) {
                return;
              }
              applyStatus(nextStatus);
              if (nextStatus.error_message) {
                setError(nextStatus.error_message);
              }
            },
          });
          if (cancelled) {
            return;
          }
          setBuildStatus(result.status);
          setSlideCount(result.slide_count);
          if (result.status === "failed" && result.error_message) {
            setError(result.error_message);
          }
          onPresentationsChanged?.();
        }
      } catch (err) {
        if (!cancelled) {
          clearActivePresentationId();
          if (isPresentationNotFoundError(err)) {
            clearCurrentPresentationState();
          } else {
            setError(err instanceof ApiError ? err.message : "Не удалось восстановить презентацию");
          }
        }
      } finally {
        if (!cancelled) {
          setIsBuilding(false);
        }
      }
    }

    void resumeActivePresentation();

    return () => {
      cancelled = true;
    };
  }, [onPresentationsChanged]);

  function clearCurrentPresentationState() {
    clearActivePresentationId();
    setPrompt("");
    setSourceFiles([]);
    setOutline(null);
    setSavedOutline(null);
    setPresentationId(null);
    setPresentationTitle("Презентация");
    setBuildStatus(null);
    setBuildTemplateFileType(null);
    setSlideCount(null);
    setBuildStage(null);
    setIsBuilding(false);
    setIsDownloading(false);
    setError(null);
  }

  function handleSourceFilesChange(event: React.ChangeEvent<HTMLInputElement>) {
    const files = Array.from(event.target.files ?? []);
    event.target.value = "";
    if (files.length === 0) {
      return;
    }

    const invalid = files.find((file) => !isAllowedSourceFile(file));
    if (invalid) {
      setError("Допустимы файлы Word (.docx), PDF, Markdown и TXT");
      return;
    }

    setSourceFiles((prev) => {
      const merged = [...prev, ...files].slice(0, MAX_SOURCE_FILES);
      if (prev.length + files.length > MAX_SOURCE_FILES) {
        setError(`Не более ${MAX_SOURCE_FILES} файлов`);
      } else {
        setError(null);
      }
      return merged;
    });
  }

  function removeSourceFile(index: number) {
    setSourceFiles((prev) => prev.filter((_, i) => i !== index));
  }

  async function persistOutline(): Promise<boolean> {
    if (!presentationId || !outline?.trim()) {
      setError("План не может быть пустым");
      return false;
    }

    setIsSavingOutline(true);
    setError(null);
    try {
      const result = await updatePresentationOutline(presentationId, outline.trim());
      setOutline(result.outline);
      setSavedOutline(result.outline);
      setPresentationTitle(result.title);
      setBuildStatus(result.status);
      setSlideCount(null);
      return true;
    } catch (err) {
      if (isPresentationNotFoundError(err)) {
        clearCurrentPresentationState();
      } else {
        setError(err instanceof ApiError ? err.message : "Не удалось сохранить план");
      }
      return false;
    } finally {
      setIsSavingOutline(false);
    }
  }

  async function handleSaveOutline() {
    await persistOutline();
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (!prompt.trim() && sourceFiles.length === 0) {
      setError("Введите описание или приложите файл");
      return;
    }

    setIsCreating(true);
    clearWorkspaceReset();
    setError(null);
    setNotice(null);
    setOutline(null);
    setSavedOutline(null);
    setPresentationId(null);
    setBuildStatus(null);
    setBuildTemplateFileType(null);
    setSlideCount(null);

    try {
      const result = await createPresentation({
        prompt: prompt.trim(),
        agentId,
        templateId: selectedTemplateId,
        sourceFiles,
      });
      setOutline(result.outline);
      setSavedOutline(result.outline);
      setPresentationId(result.id);
      saveActivePresentationId(result.id);
      setBuildStatus(result.status);
      setBuildTemplateFileType(result.template_file_type);
      setPresentationTitle(outlineTitleFromMarkdown(result.outline));
      onPresentationsChanged?.();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Не удалось создать презентацию");
    } finally {
      setIsCreating(false);
    }
  }

  async function handleBuild() {
    if (!presentationId) {
      return;
    }

    if (isOutlineDirty) {
      const saved = await persistOutline();
      if (!saved) {
        return;
      }
    }

    if (effectiveTemplateType !== null && effectiveTemplateType !== "pptx" && effectiveTemplateType !== "pdf") {
      setError("Для сборки выберите шаблон в формате PPTX или PDF");
      return;
    }

    setIsBuilding(true);
    setError(null);
    setNotice(null);
    setBuildStatus("building");
    setBuildStage("queued");

    try {
      const result = await buildPresentation(presentationId, {
        generateImages,
        onPoll: (status) => {
          setBuildStage(status.build_stage);
          setBuildStatus(status.status);
          if (status.error_message) {
            setError(status.error_message);
          }
        },
      });
      setBuildStatus(result.status);
      setSlideCount(result.slide_count);
      onPresentationsChanged?.();
      if (result.status === "failed" && result.error_message) {
        setError(result.error_message);
      }
    } catch (err) {
      if (isPresentationNotFoundError(err)) {
        clearCurrentPresentationState();
      } else {
        setBuildStatus("failed");
        setError(err instanceof ApiError ? err.message : "Не удалось собрать презентацию");
      }
    } finally {
      setIsBuilding(false);
    }
  }

  async function handleDownload() {
    if (!presentationId) {
      return;
    }
    setIsDownloading(true);
    setError(null);
    try {
      await downloadPresentation(presentationId, presentationTitle);
    } catch (err) {
      if (isPresentationNotFoundError(err)) {
        clearCurrentPresentationState();
      } else {
        setError(err instanceof ApiError ? err.message : "Не удалось скачать файл");
      }
    } finally {
      setIsDownloading(false);
    }
  }

  function handleSavePresentation() {
    if (!presentationId || buildStatus !== "ready") {
      return;
    }
    clearWorkspaceReset();
    saveActivePresentationId(presentationId);
    setNotice("Презентация сохранена и доступна в списке «Мои презентации»");
    onPresentationsChanged?.();
  }

  function handleFullReset() {
    const confirmed = window.confirm(
      "Очистить текущую рабочую область и план на экране? Сохранённые презентации останутся в списке.",
    );
    if (!confirmed) {
      return;
    }
    markWorkspaceReset();
    clearCurrentPresentationState();
    setNotice("Рабочая область очищена. Сохранённые презентации остались в списке.");
  }

  const planDisabled = isBuilding || isSavingOutline;

  return (
    <section className="overflow-hidden rounded-2xl border border-[var(--border)] bg-[var(--surface)] shadow-sm">
      <div className="border-b border-[var(--border)] px-4 sm:px-6 py-4">
        <h2 className="text-lg font-semibold text-[var(--foreground)]">Новая презентация</h2>
        <p className="mt-1 text-sm text-[var(--muted)]">
          План и итоговая презентация — не более 10 слайдов. Сгенерируйте план, отредактируйте и соберите PPTX.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="px-4 sm:px-6 py-5 space-y-4">
        <div>
          <label htmlFor="presentation-prompt" className="mb-1.5 block text-sm font-medium text-[var(--foreground)]">
            Описание презентации
          </label>
          <textarea
            id="presentation-prompt"
            value={prompt}
            onChange={(event) => setPrompt(event.target.value)}
            rows={4}
            placeholder="Например: презентация о запуске нового продукта для инвесторов, 10 слайдов…"
            className="min-h-[100px] w-full resize-y rounded-xl border border-[var(--border)] bg-[var(--background)] px-4 py-3 text-sm text-[var(--foreground)] outline-none transition-colors placeholder:text-[var(--subtle)] focus:border-[var(--primary)] focus:ring-2 focus:ring-[color:var(--focus-ring)]"
          />
        </div>

        <div className="flex flex-wrap items-center gap-2 sm:gap-3">
          <button
            type="button"
            onClick={() => sourceInputRef.current?.click()}
            disabled={sourceFiles.length >= MAX_SOURCE_FILES}
            className="rounded-lg border border-[var(--border)] bg-[var(--surface-muted)] px-3 py-2 text-sm font-medium text-[var(--primary)] transition-colors hover:border-[var(--primary)] hover:bg-[var(--accent-light)] disabled:opacity-50"
          >
            + Добавить файл
          </button>
          <input
            ref={sourceInputRef}
            type="file"
            multiple
            accept={SOURCE_ACCEPT}
            className="hidden"
            onChange={handleSourceFilesChange}
          />

          <div className="flex w-full flex-col gap-2 sm:w-auto sm:flex-row sm:items-center">
            <span className="text-sm text-[var(--muted)]">ИИ:</span>
            <select
              value={agentId}
              onChange={(event) => setAgentId(event.target.value as AgentId)}
              disabled={isLoadingAgents}
              className="rounded-lg border border-[var(--border)] bg-[var(--background)] px-2 py-1.5 text-sm text-[var(--foreground)] outline-none focus:border-[var(--primary)]"
            >
              {agents.map((agent) => (
                <option key={agent.id} value={agent.id} disabled={!agent.available}>
                  {AGENT_LABELS[agent.id]}
                  {!agent.available ? " (недоступен)" : ""}
                </option>
              ))}
            </select>
          </div>
        </div>

        {sourceFiles.length > 0 ? (
          <ul className="space-y-1.5">
            {sourceFiles.map((file, index) => (
              <li
                key={`${file.name}-${index}`}
                className="flex items-center justify-between rounded-lg bg-[var(--surface-muted)] px-3 py-2 text-sm"
              >
                <span className="truncate text-[var(--foreground)]">{file.name}</span>
                <button
                  type="button"
                  onClick={() => removeSourceFile(index)}
                  className="ml-2 shrink-0 text-xs text-[var(--danger-text)] hover:opacity-80"
                >
                  Убрать
                </button>
              </li>
            ))}
          </ul>
        ) : null}

        <div className="rounded-lg bg-[var(--surface-muted)] px-3 py-2 text-sm text-[var(--muted)]">
          {selectedTemplate ? (
            <>
              Шаблон:{" "}
              <span className="font-medium text-[var(--foreground)]">{selectedTemplate.name}</span>
              <span className="ml-1 text-[var(--subtle)]">({selectedTemplate.file_type.toUpperCase()})</span>
              {selectedTemplate.file_type === "pdf" ? (
                <span className="mt-1 block text-[var(--muted)]">
                  PDF: оформление (фон, цвета, шрифты) возьмём из первой страницы
                </span>
              ) : null}
            </>
          ) : (
            <span className="text-[var(--subtle)]">
              Шаблон не выбран — будет использован ДВФУ-шаблон по умолчанию
            </span>
          )}
        </div>

        {error ? (
          <ErrorMessage>{error}</ErrorMessage>
        ) : null}
        {notice ? (
          <p className="rounded-lg border border-[var(--success-border)] bg-[var(--success-bg)] px-3 py-2 text-sm text-[var(--success-text)]">{notice}</p>
        ) : null}

        <button
          type="submit"
          disabled={isCreating}
          className="w-full rounded-xl bg-gradient-to-r from-[var(--primary)] to-[var(--accent)] px-4 py-3 text-sm font-semibold text-[var(--on-primary)] shadow-lg shadow-[color:var(--primary)]/20 transition-all hover:from-[var(--primary-dark)] hover:to-[var(--primary)] disabled:opacity-60"
        >
          {isCreating ? "Генерация плана…" : "Сгенерировать план"}
        </button>
      </form>

      {outline ? (
        <div className="space-y-4 border-t border-[var(--border)] bg-[var(--surface-muted)] px-4 sm:px-6 py-5">
          <PresentationPlanEditor
            outline={outline}
            onOutlineChange={setOutline}
            onSave={handleSaveOutline}
            isDirty={isOutlineDirty}
            isSaving={isSavingOutline}
            disabled={planDisabled}
          />

          <label className="flex cursor-pointer items-start gap-3 rounded-xl border border-[var(--border)] bg-[var(--surface)] px-4 py-3 transition-colors hover:border-[var(--primary)]">
            <input
              type="checkbox"
              checked={generateImages}
              onChange={(event) => setGenerateImages(event.target.checked)}
              disabled={isBuilding}
              className="mt-0.5 h-4 w-4 rounded border-[var(--border)] text-[var(--primary)] focus:ring-[color:var(--focus-ring)]"
            />
            <span className="text-sm text-[var(--foreground)]">
              <span className="font-medium text-[var(--foreground)]">Генерировать иллюстрации</span>
              <span className="mt-0.5 block text-[var(--muted)]">
                ИИ создаст картинки для части слайдов (Polza). Снимите галочку, чтобы собрать только текст и
                оформление — быстрее и без запросов к генератору изображений.
              </span>
            </span>
          </label>

          <div className="flex flex-col sm:flex-row gap-2">
            <button
              type="button"
              onClick={handleBuild}
              disabled={isBuilding || buildStatus === "ready"}
              title={buildDisabledReason ?? undefined}
              className={`flex-1 rounded-xl border border-[var(--border)] bg-[var(--surface)] px-4 py-3 text-sm font-semibold text-[var(--primary)] transition-colors ${
                canBuild && !isBuilding ? "hover:border-[var(--primary)] hover:bg-[var(--surface-muted)]" : "opacity-70"
              } disabled:opacity-50 disabled:cursor-not-allowed`}
            >
              {isBuilding
                ? `Сборка: ${buildStageLabel(buildStage)}…`
                : buildStatus === "ready"
                  ? "Презентация собрана"
                  : "Собрать презентацию (.pptx)"}
            </button>

            {buildStatus === "ready" ? (
              <button
                type="button"
                onClick={handleDownload}
                disabled={isDownloading}
                className="flex-1 rounded-xl bg-[var(--success-text)] px-4 py-3 text-sm font-semibold text-[var(--surface)] transition-colors hover:opacity-90 disabled:opacity-60"
              >
                {isDownloading ? "Скачивание…" : "Скачать .pptx"}
              </button>
            ) : null}
          </div>

          {!canBuild && buildDisabledReason ? (
            <p className="text-sm text-amber-700">{buildDisabledReason}</p>
          ) : null}

          {buildStatus === "ready" && slideCount !== null ? (
            <p className="text-sm text-[var(--success-text)]">
              Готово: {slideCount} слайд(ов). После правки плана сохраните его и соберите файл заново.
            </p>
          ) : null}

          {buildStatus === "ready" ? (
            <div className="grid gap-2 sm:grid-cols-2">
              <button
                type="button"
                onClick={handleSavePresentation}
                className="rounded-xl bg-[var(--primary)] px-4 py-3 text-sm font-semibold text-[var(--on-primary)] transition-colors hover:bg-[var(--primary-dark)]"
              >
                Сохранить презентацию
              </button>
              <button
                type="button"
                onClick={handleFullReset}
                className="rounded-xl border border-[var(--danger-border)] bg-[var(--danger-bg)] px-4 py-3 text-sm font-semibold text-[var(--danger-text)] transition-colors hover:opacity-85"
              >
                Полный сброс презентации и плана
              </button>
            </div>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}
