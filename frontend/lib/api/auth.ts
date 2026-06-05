const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  retryAfterSeconds?: number;

  constructor(message: string, status: number, retryAfterSeconds?: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.retryAfterSeconds = retryAfterSeconds;
  }
}

function parseApiError(data: unknown, fallback: string): string {
  if (!data || typeof data !== "object") {
    return fallback;
  }

  const detail = (data as { detail?: unknown }).detail;

  if (typeof detail === "string") {
    return detail;
  }

  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) => {
        if (item && typeof item === "object" && "msg" in item) {
          return String((item as { msg: unknown }).msg);
        }
        return null;
      })
      .filter(Boolean);

    if (messages.length > 0) {
      return messages.join(". ");
    }
  }

  return fallback;
}

export async function apiPost<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    const retryAfterHeader = response.headers.get("Retry-After");
    const retryAfterSeconds = retryAfterHeader ? Number.parseInt(retryAfterHeader, 10) : undefined;
    throw new ApiError(
      parseApiError(errorData, "Ошибка запроса"),
      response.status,
      Number.isFinite(retryAfterSeconds) ? retryAfterSeconds : undefined,
    );
  }

  return (await response.json()) as T;
}

async function fetchAvailability(path: string, param: string, value: string): Promise<boolean> {
  const url = new URL(`${API_URL}${path}`);
  url.searchParams.set(param, value);

  const response = await fetch(url.toString(), { method: "GET" });

  if (!response.ok) {
    throw new Error("availability_check_failed");
  }

  const data = (await response.json()) as { available: boolean };
  return data.available;
}

export async function checkUsernameAvailable(username: string): Promise<boolean> {
  return fetchAvailability("/api/auth/check-username", "username", username.trim());
}

export async function checkEmailAvailable(email: string): Promise<boolean> {
  return fetchAvailability("/api/auth/check-email", "email", email.trim().toLowerCase());
}

export type MessageResponse = { message: string };
export type TokenResponse = {
  access_token: string;
  refresh_token: string;
  token_type: string;
};
export type UserMeResponse = {
  id: number;
  username: string;
  email: string;
  full_name: string | null;
  profile_image: string | null;
  role: "user" | "admin" | string;
};

export async function requestRegistrationCode(payload: {
  username: string;
  email: string;
  password: string;
}): Promise<MessageResponse> {
  return apiPost<MessageResponse>("/api/auth/register/request", {
    username: payload.username.trim(),
    email: payload.email.trim().toLowerCase(),
    password: payload.password,
  });
}

export async function resendRegistrationCode(email: string): Promise<MessageResponse> {
  return apiPost<MessageResponse>("/api/auth/register/resend", {
    email: email.trim().toLowerCase(),
  });
}

export async function verifyRegistration(payload: {
  email: string;
  code: string;
}): Promise<TokenResponse> {
  return apiPost<TokenResponse>("/api/auth/register/verify", {
    email: payload.email.trim().toLowerCase(),
    code: payload.code.trim(),
  });
}

export async function login(payload: {
  username: string;
  password: string;
}): Promise<TokenResponse> {
  return apiPost<TokenResponse>("/api/auth/login", {
    username: payload.username.trim(),
    password: payload.password,
  });
}

export async function refreshAuthTokens(refreshToken: string): Promise<TokenResponse> {
  return apiPost<TokenResponse>("/api/auth/refresh", {
    refresh_token: refreshToken,
  });
}

export async function requestPasswordResetCode(email: string): Promise<MessageResponse> {
  return apiPost<MessageResponse>("/api/auth/password-reset/request", {
    email: email.trim().toLowerCase(),
  });
}

export async function resendPasswordResetCode(email: string): Promise<MessageResponse> {
  return apiPost<MessageResponse>("/api/auth/password-reset/resend", {
    email: email.trim().toLowerCase(),
  });
}

export async function confirmPasswordReset(payload: {
  email: string;
  code: string;
  password: string;
  password_confirm: string;
}): Promise<MessageResponse> {
  return apiPost<MessageResponse>("/api/auth/password-reset/confirm", {
    email: payload.email.trim().toLowerCase(),
    code: payload.code.trim(),
    password: payload.password,
    password_confirm: payload.password_confirm,
  });
}

export async function fetchMe(accessToken: string): Promise<UserMeResponse> {
  const response = await fetch(`${API_URL}/api/auth/me`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new ApiError(parseApiError(errorData, "Ошибка авторизации"), response.status);
  }

  return (await response.json()) as UserMeResponse;
}

export async function updateMe(
  accessToken: string,
  payload: { username: string; full_name?: string | null },
): Promise<UserMeResponse> {
  const response = await fetch(`${API_URL}/api/auth/me`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${accessToken}`,
    },
    body: JSON.stringify({
      username: payload.username.trim(),
      full_name: payload.full_name?.trim() || null,
    }),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new ApiError(parseApiError(errorData, "Не удалось обновить профиль"), response.status);
  }

  return (await response.json()) as UserMeResponse;
}

export async function uploadProfileImage(
  accessToken: string,
  image: File,
): Promise<UserMeResponse> {
  const formData = new FormData();
  formData.append("image", image);

  const response = await fetch(`${API_URL}/api/auth/me/profile-image`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
    body: formData,
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new ApiError(parseApiError(errorData, "Не удалось загрузить фото"), response.status);
  }

  return (await response.json()) as UserMeResponse;
}

export async function deleteProfileImage(accessToken: string): Promise<UserMeResponse> {
  const response = await fetch(`${API_URL}/api/auth/me/profile-image`, {
    method: "DELETE",
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new ApiError(parseApiError(errorData, "Не удалось удалить фото"), response.status);
  }

  return (await response.json()) as UserMeResponse;
}

export async function deleteCurrentAccount(accessToken: string): Promise<MessageResponse> {
  const response = await fetch(`${API_URL}/api/auth/me`, {
    method: "DELETE",
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new ApiError(parseApiError(errorData, "Не удалось удалить аккаунт"), response.status);
  }

  return (await response.json()) as MessageResponse;
}
