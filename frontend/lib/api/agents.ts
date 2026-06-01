import { ApiError } from "@/lib/api/auth";
import { getAccessToken } from "@/lib/auth/token";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

function parseApiError(data: unknown, fallback: string): string {
  if (!data || typeof data !== "object") {
    return fallback;
  }
  const detail = (data as { detail?: unknown }).detail;
  if (typeof detail === "string") {
    return detail;
  }
  return fallback;
}

async function apiAuthFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = getAccessToken();
  if (!token) {
    throw new ApiError("Требуется авторизация", 401);
  }

  const headers = new Headers(init.headers);
  headers.set("Authorization", `Bearer ${token}`);
  if (init.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(`${API_URL}${path}`, { ...init, headers });

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new ApiError(parseApiError(errorData, "Ошибка запроса"), response.status);
  }

  return (await response.json()) as T;
}

export type AgentId = "ollama" | "gemini" | "mimo" | "polza";

export type AgentInfo = {
  id: AgentId;
  name: string;
  description: string;
  model: string;
  provider: string;
  available: boolean;
  unavailable_reason: string | null;
};

export type ChatMessage = {
  role: "user" | "assistant";
  content: string;
};

export type AgentChatResponse = {
  agent_id: AgentId;
  model: string;
  reply: string;
};

export async function fetchAgents(): Promise<AgentInfo[]> {
  return apiAuthFetch<AgentInfo[]>("/api/agents");
}

export async function chatWithAgent(payload: {
  agent_id: AgentId;
  message: string;
  history: ChatMessage[];
}): Promise<AgentChatResponse> {
  return apiAuthFetch<AgentChatResponse>("/api/agents/chat", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
