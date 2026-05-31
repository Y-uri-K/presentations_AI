import { ApiError } from "@/lib/api/auth";
import { getAccessToken } from "@/lib/auth/token";
import type { AgentId } from "@/lib/api/agents";

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

export type PresentationCreateResponse = {
  outline: string;
  agent_id: AgentId;
  template_id: number | null;
  template_name: string | null;
  source_files: string[];
};

export async function createPresentation(payload: {
  prompt: string;
  agentId: AgentId;
  templateId: number | null;
  sourceFiles: File[];
}): Promise<PresentationCreateResponse> {
  const token = getAccessToken();
  if (!token) {
    throw new ApiError("Требуется авторизация", 401);
  }

  const formData = new FormData();
  formData.append("prompt", payload.prompt);
  formData.append("agent_id", payload.agentId);
  if (payload.templateId !== null) {
    formData.append("template_id", String(payload.templateId));
  }
  for (const file of payload.sourceFiles) {
    formData.append("source_files", file);
  }

  const response = await fetch(`${API_URL}/api/presentations/create`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: formData,
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new ApiError(parseApiError(errorData, "Не удалось создать презентацию"), response.status);
  }

  return (await response.json()) as PresentationCreateResponse;
}
