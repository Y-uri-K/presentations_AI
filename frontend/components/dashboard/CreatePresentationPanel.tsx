"use client";

import { useEffect, useRef, useState } from "react";

import {
  type AgentId,
  type AgentInfo,
  fetchAgents,
} from "@/lib/api/agents";
import { ApiError } from "@/lib/api/auth";
import { createPresentation } from "@/lib/api/presentations";
import { pickPreferredAgent } from "@/lib/agents/pickPreferredAgent";
import { useTemplateSelection } from "@/components/dashboard/TemplateSelectionContext";

const AGENT_LABELS: Record<AgentId, string> = {
  ollama: "Ollama",
  gemini: "Gemini",
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
  const [agentId, setAgentId] = useState<AgentId>("mimo");
  const [prompt, setPrompt] = useState("");
  const [sourceFiles, setSourceFiles] = useState<File[]>([]);
  const [outline, setOutline] = useState<string | null>(null);
  const [isLoadingAgents, setIsLoadingAgents] = useState(true);
  const [isCreating, setIsCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

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

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (!prompt.trim() && sourceFiles.length === 0) {
      setError("Введите описание или приложите файл");
      return;
    }

    setIsCreating(true);
    setError(null);
    setOutline(null);

    try {
      const result = await createPresentation({
        prompt: prompt.trim(),
        agentId,
        templateId: selectedTemplateId,
        sourceFiles,
      });
      setOutline(result.outline);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Не удалось создать презентацию");
    } finally {
      setIsCreating(false);
    }
  }

  return (
    <section className="rounded-2xl border border-slate-200 bg-white shadow-sm overflow-hidden">
      <div className="border-b border-slate-100 px-6 py-4">
        <h2 className="text-lg font-semibold text-slate-900">Новая презентация</h2>
        <p className="text-sm text-slate-500 mt-1">
          Опишите тему и при необходимости приложите материалы Word, PDF, Markdown или TXT
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
            </>
          ) : (
            <span className="text-slate-400">Шаблон не выбран — выберите в блоке «Шаблоны»</span>
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
          {isCreating ? "Генерация плана…" : "Создать презентацию"}
        </button>
      </form>

      {outline ? (
        <div className="border-t border-slate-100 px-6 py-5 bg-slate-50/50">
          <h3 className="text-sm font-semibold text-slate-800 mb-3">План презентации</h3>
          <pre className="whitespace-pre-wrap text-sm text-slate-700 leading-relaxed font-sans">
            {outline}
          </pre>
        </div>
      ) : null}
    </section>
  );
}
