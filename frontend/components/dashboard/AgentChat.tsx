"use client";

import { useEffect, useRef, useState } from "react";

import {
  type AgentId,
  type AgentInfo,
  type ChatMessage,
  chatWithAgent,
  fetchAgents,
} from "@/lib/api/agents";
import { ApiError } from "@/lib/api/auth";

const AGENT_LABELS: Record<AgentId, string> = {
  ollama: "Ollama",
  gemini: "Gemini 3.5 Flash (Polza)",
  polza: "Gemini 3.5 Flash (Polza)",
  mimo: "MiMo",
};

export function AgentChat() {
  const [agents, setAgents] = useState<AgentInfo[]>([]);
  const [selectedAgentId, setSelectedAgentId] = useState<AgentId>("ollama");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [isLoadingAgents, setIsLoadingAgents] = useState(true);
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const selectedAgent = agents.find((agent) => agent.id === selectedAgentId);

  useEffect(() => {
    fetchAgents()
      .then((list) => {
        setAgents(list);
        const firstAvailable = list.find((agent) => agent.available);
        if (firstAvailable) {
          setSelectedAgentId(firstAvailable.id);
        }
      })
      .catch((err) => {
        setError(err instanceof ApiError ? err.message : "Не удалось загрузить агентов");
      })
      .finally(() => setIsLoadingAgents(false));
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isSending]);

  function handleAgentChange(agentId: AgentId) {
    setSelectedAgentId(agentId);
    setMessages([]);
    setError(null);
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    const text = input.trim();
    if (!text || isSending || !selectedAgent?.available) {
      return;
    }

    setInput("");
    setError(null);
    setIsSending(true);

    const userMessage: ChatMessage = { role: "user", content: text };
    setMessages((prev) => [...prev, userMessage]);

    try {
      const response = await chatWithAgent({
        agent_id: selectedAgentId,
        message: text,
        history: messages,
      });
      setMessages((prev) => [...prev, { role: "assistant", content: response.reply }]);
    } catch (err) {
      setMessages((prev) => prev.slice(0, -1));
      setInput(text);
      setError(err instanceof ApiError ? err.message : "Не удалось получить ответ");
    } finally {
      setIsSending(false);
    }
  }

  return (
    <section className="overflow-hidden rounded-2xl border border-[var(--border)] bg-[var(--surface)] shadow-sm">
      <div className="flex flex-col gap-4 border-b border-[var(--border)] px-6 py-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-lg font-semibold text-[var(--foreground)]">ИИ-агенты</h2>
          <p className="text-sm text-[var(--muted)]">Выберите модель и задайте вопрос</p>
        </div>

        <div className="flex flex-wrap gap-2">
          {isLoadingAgents ? (
            <span className="text-sm text-[var(--subtle)]">Загрузка…</span>
          ) : (
            agents.map((agent) => (
              <button
                key={agent.id}
                type="button"
                onClick={() => handleAgentChange(agent.id)}
                disabled={!agent.available}
                title={agent.unavailable_reason ?? agent.description}
                className={`rounded-lg px-3 py-1.5 text-sm font-medium transition-colors ${
                  selectedAgentId === agent.id
                    ? "bg-[var(--primary)] text-[var(--on-primary)]"
                    : agent.available
                      ? "border border-[var(--border)] text-[var(--foreground)] hover:border-[var(--primary)] hover:bg-[var(--surface-muted)]"
                      : "cursor-not-allowed border border-[var(--border)] text-[var(--subtle)] opacity-60"
                }`}
              >
                {AGENT_LABELS[agent.id]}
                {!agent.available ? " ✕" : ""}
              </button>
            ))
          )}
        </div>
      </div>

      {selectedAgent ? (
        <div className="border-b border-[var(--border)] bg-[var(--surface-muted)] px-6 py-2 text-xs text-[var(--muted)]">
          {selectedAgent.description}
          {selectedAgent.available ? (
            <span className="ml-2 text-[var(--subtle)]">· модель: {selectedAgent.model}</span>
          ) : (
            <span className="ml-2 text-amber-600">· {selectedAgent.unavailable_reason}</span>
          )}
        </div>
      ) : null}

      <div className="h-80 space-y-4 overflow-y-auto bg-[var(--surface-muted)] px-6 py-4">
        {messages.length === 0 ? (
          <p className="py-12 text-center text-sm text-[var(--subtle)]">
            Напишите сообщение, чтобы начать диалог с выбранным агентом
          </p>
        ) : (
          messages.map((message, index) => (
            <div
              key={`${message.role}-${index}`}
              className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}
            >
              <div
                className={`max-w-[85%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed whitespace-pre-wrap ${
                  message.role === "user"
                    ? "bg-[var(--primary)] text-[var(--on-primary)]"
                    : "border border-[var(--border)] bg-[var(--surface)] text-[var(--foreground)]"
                }`}
              >
                {message.content}
              </div>
            </div>
          ))
        )}
        {isSending ? (
          <p className="animate-pulse text-sm text-[var(--subtle)]">Агент печатает…</p>
        ) : null}
        <div ref={messagesEndRef} />
      </div>

      {error ? (
        <p className="mx-6 mb-2 rounded-lg border border-[var(--danger-border)] bg-[var(--danger-bg)] px-3 py-2 text-sm text-[var(--danger-text)]">{error}</p>
      ) : null}

      <form onSubmit={handleSubmit} className="flex gap-3 border-t border-[var(--border)] px-6 py-4">
        <input
          type="text"
          value={input}
          onChange={(event) => setInput(event.target.value)}
          placeholder={
            selectedAgent?.available
              ? `Сообщение для ${AGENT_LABELS[selectedAgentId]}…`
              : "Агент недоступен"
          }
          disabled={isSending || !selectedAgent?.available}
          className="flex-1 rounded-xl border border-[var(--border)] bg-[var(--background)] px-4 py-2.5 text-sm text-[var(--foreground)] outline-none placeholder:text-[var(--subtle)] focus:border-[var(--primary)] focus:ring-2 focus:ring-[color:var(--focus-ring)] disabled:bg-[var(--surface-muted)] disabled:text-[var(--subtle)]"
        />
        <button
          type="submit"
          disabled={isSending || !selectedAgent?.available || !input.trim()}
          className="rounded-xl bg-[var(--primary)] px-5 py-2.5 text-sm font-semibold text-[var(--on-primary)] transition-colors hover:bg-[var(--primary-dark)] disabled:cursor-not-allowed disabled:opacity-50"
        >
          {isSending ? "…" : "Отправить"}
        </button>
      </form>
    </section>
  );
}
