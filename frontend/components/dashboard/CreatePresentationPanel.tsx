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
  updatePresentationOutline,
  type PresentationStatus,
} from "@/lib/api/presentations";
import { pickPreferredAgent } from "@/lib/agents/pickPreferredAgent";
import { PresentationPlanEditor } from "@/components/dashboard/PresentationPlanEditor";
import { useTemplateSelection } from "@/components/dashboard/TemplateSelectionContext";
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
  ollama: "Ollama",
  gemini: "Gemini 3.5 Flash (Polza)",
  polza: "Gemini 3.5 Flash (Polza)",
  mimo: "MiMo",
};

const SOURCE_ACCEPT =
  ".docx,.pdf,.md,.markdown,.txt,application/pdf,text/plain,text/markdown,application/vnd.openxmlformats-officedocument.wordprocessingml.document";

const MAX_SOURCE_FILES = 5;

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

export function CreatePresentationPanel() {
  const sourceInputRef = useRef<HTMLInputElement>(null);
  const { selectedTemplate, selectedTemplateId } = useTemplateSelection();

  const [agents, setAgents] = useState<AgentInfo[]>([]);
  const [agentId, setAgentId] = useState<AgentId>("gemini");
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
    (effectiveTemplateType === "pptx" || effectiveTemplateType === "pdf") &&
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
        : effectiveTemplateType === null
          ? "Выберите шаблон (PPTX или PDF) в блоке «Шаблоны» и сгенерируйте план заново"
          : effectiveTemplateType !== "pptx" && effectiveTemplateType !== "pdf"
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
      setError(err instanceof ApiError ? err.message : "Не удалось сохранить план");
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
    setError(null);
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
      setBuildStatus(result.status);
      setBuildTemplateFileType(result.template_file_type);
      setPresentationTitle(outlineTitleFromMarkdown(result.outline));
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

    if (effectiveTemplateType !== "pptx" && effectiveTemplateType !== "pdf") {
      setError("Для сборки выберите шаблон в формате PPTX или PDF");
      return;
    }

    setIsBuilding(true);
    setError(null);
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
      if (result.status === "failed" && result.error_message) {
        setError(result.error_message);
      }
    } catch (err) {
      setBuildStatus("failed");
      setError(err instanceof ApiError ? err.message : "Не удалось собрать презентацию");
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
      setError(err instanceof ApiError ? err.message : "Не удалось скачать файл");
    } finally {
      setIsDownloading(false);
    }
  }

  const planDisabled = isBuilding || isSavingOutline;

  return (
    <section className="rounded-2xl border border-slate-200 bg-white shadow-sm overflow-hidden">
      <div className="border-b border-slate-100 px-6 py-4">
        <h2 className="text-lg font-semibold text-slate-900">Новая презентация</h2>
        <p className="text-sm text-slate-500 mt-1">
          План и итоговая презентация — не более 10 слайдов. Сгенерируйте план, отредактируйте и соберите PPTX.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="px-6 py-5 space-y-4">
        <div>
          <label htmlFor="presentation-prompt" className="block text-sm font-medium text-slate-700 mb-1.5">
            Описание презентации
          </label>
          <textarea
            id="presentation-prompt"
            value={prompt}
            onChange={(event) => setPrompt(event.target.value)}
            rows={4}
            placeholder="Например: презентация о запуске нового продукта для инвесторов, 10 слайдов…"
            className="w-full rounded-xl border border-slate-200 px-4 py-3 text-sm outline-none focus:border-sky-300 focus:ring-2 focus:ring-sky-100 resize-y min-h-[100px]"
          />
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <button
            type="button"
            onClick={() => sourceInputRef.current?.click()}
            disabled={sourceFiles.length >= MAX_SOURCE_FILES}
            className="rounded-lg border border-sky-200 bg-sky-50 px-3 py-2 text-sm font-medium text-[var(--primary)] hover:bg-sky-100 disabled:opacity-50 transition-colors"
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

          <div className="flex items-center gap-2 text-sm">
            <span className="text-slate-500">ИИ:</span>
            <select
              value={agentId}
              onChange={(event) => setAgentId(event.target.value as AgentId)}
              disabled={isLoadingAgents}
              className="rounded-lg border border-slate-200 px-2 py-1.5 text-sm outline-none focus:border-sky-300"
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
                className="flex items-center justify-between rounded-lg bg-slate-50 px-3 py-2 text-sm"
              >
                <span className="truncate text-slate-700">{file.name}</span>
                <button
                  type="button"
                  onClick={() => removeSourceFile(index)}
                  className="shrink-0 ml-2 text-xs text-red-600 hover:text-red-700"
                >
                  Убрать
                </button>
              </li>
            ))}
          </ul>
        ) : null}

        <div className="rounded-lg bg-slate-50 px-3 py-2 text-sm text-slate-600">
          {selectedTemplate ? (
            <>
              Шаблон:{" "}
              <span className="font-medium text-slate-800">{selectedTemplate.name}</span>
              <span className="text-slate-400 ml-1">({selectedTemplate.file_type.toUpperCase()})</span>
              {selectedTemplate.file_type === "pdf" ? (
                <span className="block mt-1 text-slate-500">
                  PDF: оформление (фон, цвета, шрифты) возьмём из первой страницы
                </span>
              ) : null}
            </>
          ) : (
            <span className="text-slate-400">
              Шаблон не выбран — выберите PPTX или PDF в блоке «Шаблоны»
            </span>
          )}
        </div>

        {error ? (
          <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>
        ) : null}

        <button
          type="submit"
          disabled={isCreating}
          className="w-full rounded-xl bg-gradient-to-r from-[var(--primary)] to-[#3b82f6] px-4 py-3 text-sm font-semibold text-white shadow-lg shadow-blue-500/25 hover:from-[var(--primary-dark)] hover:to-[var(--primary)] disabled:opacity-60 transition-all"
        >
          {isCreating ? "Генерация плана…" : "Сгенерировать план"}
        </button>
      </form>

      {outline ? (
        <div className="border-t border-slate-100 px-6 py-5 bg-slate-50/50 space-y-4">
          <PresentationPlanEditor
            outline={outline}
            onOutlineChange={setOutline}
            onSave={handleSaveOutline}
            isDirty={isOutlineDirty}
            isSaving={isSavingOutline}
            disabled={planDisabled}
          />

          <label className="flex items-start gap-3 rounded-xl border border-slate-200 bg-white px-4 py-3 cursor-pointer hover:border-sky-200 transition-colors">
            <input
              type="checkbox"
              checked={generateImages}
              onChange={(event) => setGenerateImages(event.target.checked)}
              disabled={isBuilding}
              className="mt-0.5 h-4 w-4 rounded border-slate-300 text-[var(--primary)] focus:ring-sky-200"
            />
            <span className="text-sm text-slate-700">
              <span className="font-medium text-slate-900">Генерировать иллюстрации</span>
              <span className="block text-slate-500 mt-0.5">
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
              className={`flex-1 rounded-xl border border-sky-200 bg-white px-4 py-3 text-sm font-semibold text-[var(--primary)] transition-colors ${
                canBuild && !isBuilding ? "hover:bg-sky-50" : "opacity-70"
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
                className="flex-1 rounded-xl bg-emerald-600 px-4 py-3 text-sm font-semibold text-white hover:bg-emerald-700 disabled:opacity-60 transition-colors"
              >
                {isDownloading ? "Скачивание…" : "Скачать .pptx"}
              </button>
            ) : null}
          </div>

          {!canBuild && buildDisabledReason ? (
            <p className="text-sm text-amber-700">{buildDisabledReason}</p>
          ) : null}

          {buildStatus === "ready" && slideCount !== null ? (
            <p className="text-sm text-emerald-700">
              Готово: {slideCount} слайд(ов). После правки плана сохраните его и соберите файл заново.
            </p>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}
