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

  const response = await fetch(`${API_URL}${path}`, { ...init, headers });

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new ApiError(parseApiError(errorData, "Ошибка запроса"), response.status);
  }

  return (await response.json()) as T;
}

export type TemplateFileType = "pptx" | "pdf";

export type TemplateListItem = {
  id: number;
  name: string;
  original_filename: string;
  file_type: TemplateFileType;
  mime_type: string;
  size_bytes: number;
  created_at: string;
};

export type PublicTemplateSort = "new" | "name" | "downloads" | "rating";

export type PublicTemplateListItem = TemplateListItem & {
  author_username: string;
  download_count: number;
  rating_avg: number;
  rating_count: number;
  user_rating: number | null;
};

export type TemplatePreview = {
  template_id: number;
  name: string;
  file_type: TemplateFileType;
  original_filename: string;
  size_bytes: number;
  download_count: number;
  preview_kind: "image" | "metadata" | "office";
  image_data_url: string | null;
  file_view_url: string | null;
  office_viewer_url: string | null;
};

export async function fetchTemplates(): Promise<TemplateListItem[]> {
  return apiAuthFetch<TemplateListItem[]>("/api/templates");
}

export async function fetchPublicTemplates(options: {
  search?: string;
  sort?: PublicTemplateSort;
} = {}): Promise<PublicTemplateListItem[]> {
  const params = new URLSearchParams();
  if (options.search?.trim()) {
    params.set("search", options.search.trim());
  }
  if (options.sort) {
    params.set("sort", options.sort);
  }
  const query = params.toString();
  return apiAuthFetch<PublicTemplateListItem[]>(`/api/templates/public${query ? `?${query}` : ""}`);
}

export async function uploadTemplate(file: File, name?: string): Promise<TemplateListItem> {
  const token = getAccessToken();
  if (!token) {
    throw new ApiError("Требуется авторизация", 401);
  }

  const formData = new FormData();
  formData.append("file", file);
  if (name?.trim()) {
    formData.append("name", name.trim());
  }

  const response = await fetch(`${API_URL}/api/templates/upload`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: formData,
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new ApiError(parseApiError(errorData, "Не удалось загрузить шаблон"), response.status);
  }

  const data = (await response.json()) as { template: TemplateListItem };
  return data.template;
}

export async function uploadPublicTemplate(
  file: File,
  name?: string,
): Promise<PublicTemplateListItem> {
  const token = getAccessToken();
  if (!token) {
    throw new ApiError("Требуется авторизация", 401);
  }

  const formData = new FormData();
  formData.append("file", file);
  if (name?.trim()) {
    formData.append("name", name.trim());
  }

  const response = await fetch(`${API_URL}/api/templates/public/upload`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: formData,
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new ApiError(parseApiError(errorData, "Не удалось загрузить шаблон"), response.status);
  }

  return (await response.json()) as PublicTemplateListItem;
}

export async function deleteTemplate(templateId: number): Promise<void> {
  await apiAuthFetch<{ message: string }>(`/api/templates/${templateId}`, {
    method: "DELETE",
  });
}

export async function renameTemplate(
  templateId: number,
  name: string,
): Promise<TemplateListItem> {
  const data = await apiAuthFetch<{ template: TemplateListItem }>(
    `/api/templates/${templateId}`,
    {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: name.trim() }),
    },
  );
  return data.template;
}

export async function downloadTemplate(template: TemplateListItem): Promise<void> {
  const token = getAccessToken();
  if (!token) {
    throw new ApiError("Требуется авторизация", 401);
  }

  const response = await fetch(`${API_URL}/api/templates/${template.id}/download`, {
    headers: { Authorization: `Bearer ${token}` },
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new ApiError(parseApiError(errorData, "Не удалось скачать шаблон"), response.status);
  }

  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = template.original_filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

export async function downloadPublicTemplate(template: PublicTemplateListItem): Promise<void> {
  const token = getAccessToken();
  if (!token) {
    throw new ApiError("Требуется авторизация", 401);
  }

  const response = await fetch(`${API_URL}/api/templates/public/${template.id}/download`, {
    headers: { Authorization: `Bearer ${token}` },
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new ApiError(parseApiError(errorData, "Не удалось скачать шаблон"), response.status);
  }

  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = template.original_filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

export async function ratePublicTemplate(
  templateId: number,
  rating: number,
): Promise<{ rating_avg: number; rating_count: number; user_rating: number }> {
  const data = await apiAuthFetch<{
    rating_avg: number;
    rating_count: number;
    user_rating: number;
  }>(`/api/templates/public/${templateId}/rating`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ rating }),
  });
  return data;
}

export async function fetchTemplatePreview(templateId: number): Promise<TemplatePreview> {
  return apiAuthFetch<TemplatePreview>(`/api/templates/public/${templateId}/preview`);
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) {
    return `${bytes} Б`;
  }
  if (bytes < 1024 * 1024) {
    return `${(bytes / 1024).toFixed(1)} КБ`;
  }
  return `${(bytes / (1024 * 1024)).toFixed(1)} МБ`;
}

export { formatFileSize };
