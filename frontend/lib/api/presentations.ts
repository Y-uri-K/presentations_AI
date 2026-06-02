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

function authHeaders(): HeadersInit {
  const token = getAccessToken();
  if (!token) {
    throw new ApiError("Требуется авторизация", 401);
  }
  return { Authorization: `Bearer ${token}` };
}

export type PresentationStatus = "draft" | "building" | "ready" | "failed";

export type PresentationCreateResponse = {
  id: number;
  outline: string;
  agent_id: AgentId;
  template_id: number | null;
  template_name: string | null;
  template_file_type: "pptx" | "pdf" | null;
  source_files: string[];
  status: PresentationStatus;
};

export type PresentationBuildResponse = {
  id: number;
  status: PresentationStatus;
  error_message: string | null;
  slide_count: number | null;
};

export type PresentationStatusResponse = {
  id: number;
  status: PresentationStatus;
  title: string;
  outline: string | null;
  template_id: number | null;
  template_name: string | null;
  template_file_type: "pptx" | "pdf" | null;
  build_stage: string | null;
  error_message: string | null;
  slide_count: number | null;
  has_download: boolean;
  created_at: string;
  updated_at: string;
};

export type PresentationListItem = {
  id: number;
  title: string;
  status: PresentationStatus;
  template_id: number | null;
  template_name: string | null;
  template_file_type: "pptx" | "pdf" | null;
  slide_count: number | null;
  has_download: boolean;
  created_at: string;
  updated_at: string;
};

export type PresentationOutlineUpdateResponse = {
  id: number;
  outline: string;
  title: string;
  status: PresentationStatus;
};

async function apiAuthFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  const auth = authHeaders();
  Object.entries(auth).forEach(([key, value]) => headers.set(key, value));

  const response = await fetch(`${API_URL}${path}`, { ...init, headers });

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new ApiError(parseApiError(errorData, "Ошибка запроса"), response.status);
  }

  return (await response.json()) as T;
}

export async function fetchPresentations(): Promise<PresentationListItem[]> {
  return apiAuthFetch<PresentationListItem[]>("/api/presentations");
}

export async function createPresentation(payload: {
  prompt: string;
  agentId: AgentId;
  templateId: number | null;
  sourceFiles: File[];
}): Promise<PresentationCreateResponse> {
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
    headers: authHeaders(),
    body: formData,
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new ApiError(parseApiError(errorData, "Не удалось создать презентацию"), response.status);
  }

  return (await response.json()) as PresentationCreateResponse;
}

export async function updatePresentationOutline(
  presentationId: number,
  outline: string,
): Promise<PresentationOutlineUpdateResponse> {
  const response = await fetch(`${API_URL}/api/presentations/${presentationId}/outline`, {
    method: "PATCH",
    headers: {
      ...authHeaders(),
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ outline }),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new ApiError(parseApiError(errorData, "Не удалось сохранить план"), response.status);
  }

  return (await response.json()) as PresentationOutlineUpdateResponse;
}

export async function renamePresentation(
  presentationId: number,
  title: string,
): Promise<PresentationListItem> {
  const data = await apiAuthFetch<{ presentation: PresentationListItem }>(
    `/api/presentations/${presentationId}`,
    {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title: title.trim() }),
    },
  );
  return data.presentation;
}

export async function deletePresentation(presentationId: number): Promise<void> {
  await apiAuthFetch<{ message: string }>(`/api/presentations/${presentationId}`, {
    method: "DELETE",
  });
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/** Запускает сборку (сразу возвращает building) и ждёт ready/failed через polling. */
export async function buildPresentation(
  presentationId: number,
  options?: {
    generateImages?: boolean;
    onPoll?: (status: PresentationStatusResponse) => void;
  },
): Promise<PresentationBuildResponse> {
  const generateImages = options?.generateImages ?? true;
  const onPoll = options?.onPoll;
  const response = await fetch(`${API_URL}/api/presentations/${presentationId}/build`, {
    method: "POST",
    headers: {
      ...authHeaders(),
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ generate_images: generateImages }),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new ApiError(parseApiError(errorData, "Не удалось собрать презентацию"), response.status);
  }

  const started = (await response.json()) as PresentationBuildResponse;
  if (started.status !== "building") {
    return started;
  }

  const deadline = Date.now() + 20 * 60 * 1000;
  while (Date.now() < deadline) {
    await sleep(3000);
    const status = await getPresentationStatus(presentationId);
    onPoll?.(status);
    if (status.status === "ready") {
      return {
        id: status.id,
        status: "ready",
        error_message: null,
        slide_count: status.slide_count,
      };
    }
    if (status.status === "failed") {
      return {
        id: status.id,
        status: "failed",
        error_message: status.error_message,
        slide_count: status.slide_count,
      };
    }
  }

  throw new ApiError(
    "Сборка занимает слишком много времени. Проверьте логи backend или повторите позже.",
    504,
  );
}

export async function getPresentationStatus(
  presentationId: number,
): Promise<PresentationStatusResponse> {
  const response = await fetch(`${API_URL}/api/presentations/${presentationId}`, {
    headers: authHeaders(),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new ApiError(parseApiError(errorData, "Не удалось получить статус"), response.status);
  }

  return (await response.json()) as PresentationStatusResponse;
}

export async function downloadPresentation(presentationId: number, title: string): Promise<void> {
  const response = await fetch(`${API_URL}/api/presentations/${presentationId}/download`, {
    headers: authHeaders(),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new ApiError(parseApiError(errorData, "Не удалось скачать файл"), response.status);
  }

  const blob = await response.blob();
  const safeTitle = title.trim() || "presentation";
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `${safeTitle}.pptx`;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}
