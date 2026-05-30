const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
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
    throw new ApiError(parseApiError(errorData, "Ошибка запроса"), response.status);
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

type MessageResponse = { message: string };
type TokenResponse = { access_token: string; token_type: string };

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
